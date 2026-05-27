"""
人資面試排程系統 - Streamlit 前端 (2026 正式上線優化版)
包含：動態應徵者表單(支援URL自動帶入)、自動生成 Google Meet、即時防雙重預約、Google Sheets 雲端連動、yagmail 面試信發送、動態日曆抓取
"""

import streamlit as st
import json
import os
import gspread
import yagmail
from datetime import datetime, timedelta, timezone
from google.oauth2.service_account import Credentials
from calendar_sync import create_interview_event
from Calendar_BusyTime_Picker import fetch_and_save_calendar_data # 🌟 新增：導入動態抓取模組

# ========== 頁面配置 ==========
st.set_page_config(page_title="人資面試排程系統", layout="wide")

st.markdown("""
    <style>
    body, p, div, button, label { font-size: 1.2rem !important; }
    .stButton > button { font-size: 1.2rem !important; padding: 10px !important; min-height: 2.5rem !important; }
    .stMarkdown h3 { font-size: 1.3rem !important; }
    </style>
""", unsafe_allow_html=True)

st.title("👔 人資面試排程系統")

WORK_SESSIONS = [(9, 12), (13, 18)]
BUFFER = timedelta(minutes=15)
INTERVIEW_LEN = timedelta(hours=1)

# ==========================================
# 🌟 雲端地雷 1 解除：動態抓取最新日曆資料 (快取 5 分鐘防 API 爆掉)
# ==========================================
@st.cache_data(ttl=300)
def get_live_calendar_data():
    target_emails = ['b10310038@g.ntu.edu.tw', 'b10310049@g.ntu.edu.tw']
    try:
        # 直接呼叫我們寫好的抓取功能，回傳最新 JSON dict
        return fetch_and_save_calendar_data(target_emails)
    except Exception as e:
        st.error(f"❌ 無法獲取主管日曆，請稍後再試。({e})")
        st.stop()

with st.spinner("🔄 正在同步主管最新行事曆，請稍候..."):
    data = get_live_calendar_data()

emails = list(data.keys())
if len(emails) < 2:
    st.error("❌ 日曆資料不足（至少需要 2 個主管）")
    st.stop()

person1 = data[emails[0]]  
person2 = data[emails[1]]  

# 組合兩人所有的忙碌行程，完美防禦跨日事件
busy_times_global = [(item["start"], item["end"]) for item in person1 + person2]

script_dir = os.path.dirname(os.path.abspath(__file__))
booking_file = os.path.join(script_dir, "bookings.json")

def load_bookings():
    if os.path.exists(booking_file):
        try:
            with open(booking_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_bookings(bookings):
    with open(booking_file, "w", encoding="utf-8") as f:
        json.dump(bookings, f, indent=4, ensure_ascii=False)
        print(f"[系統日誌] 已更新 bookings.json 預約紀錄庫。")

if "booked_global" not in st.session_state:
    st.session_state.booked_global = load_bookings()
if "confirmed" not in st.session_state:
    st.session_state.confirmed = False
if "confirmed_info" not in st.session_state:
    st.session_state.confirmed_info = None
if "selected_slot" not in st.session_state:
    st.session_state.selected_slot = None
if "meet_link" not in st.session_state:
    st.session_state.meet_link = None

def is_busy(check_start, check_end, busy_list):
    for busy_start_str, busy_end_str in busy_list:
        busy_start = datetime.fromisoformat(busy_start_str)
        busy_end = datetime.fromisoformat(busy_end_str)
        if not (check_end <= busy_start or check_start >= busy_end):
            return True  
    return False  

def is_slot_available(date_str, time_str, booked_dict):
    time_parts = time_str.split('-')
    check_start = datetime.strptime(f"{date_str} {time_parts[0]}", '%Y-%m-%d %H:%M')
    check_end = datetime.strptime(f"{date_str} {time_parts[1]}", '%Y-%m-%d %H:%M')
    check_start_with_buffer = check_start - BUFFER
    check_end_with_buffer = check_end + BUFFER

    for key in booked_dict.keys():
        booked_date, booked_time = eval(key)
        if booked_date == date_str:
            booked_parts = booked_time.split('-')
            booked_start = datetime.strptime(f"{booked_date} {booked_parts[0]}", '%Y-%m-%d %H:%M')
            booked_end = datetime.strptime(f"{booked_date} {booked_parts[1]}", '%Y-%m-%d %H:%M')
            booked_start_with_buffer = booked_start - BUFFER
            booked_end_with_buffer = booked_end + BUFFER
            if not (check_end_with_buffer <= booked_start_with_buffer or check_start_with_buffer >= booked_end_with_buffer):
                return False  
    return True  

# ==========================================
# 強制從「明天」開始生成未來 21 天的空檔
# ==========================================
tw_tz = timezone(timedelta(hours=8))
tomorrow = (datetime.now(tw_tz) + timedelta(days=1)).date()
all_dates = [tomorrow + timedelta(days=i) for i in range(21)]

available = {}
for date in all_dates:
    if date.weekday() < 5:
        for work_start, work_end in WORK_SESSIONS:
            ws = datetime.combine(date, datetime.min.time().replace(hour=work_start))
            we = datetime.combine(date, datetime.min.time().replace(hour=work_end))
            scan_start = ws + BUFFER
            scan_end = we - INTERVIEW_LEN - BUFFER
            t = scan_start
            
            while t <= scan_end:
                check_start = t - BUFFER
                check_end = t + INTERVIEW_LEN + BUFFER
                if not is_busy(check_start, check_end, busy_times_global):
                    date_str = date.strftime('%Y-%m-%d')
                    time_str = t.strftime('%H:%M')
                    end_str = (t + INTERVIEW_LEN).strftime('%H:%M')
                    available[(date_str, f"{time_str}-{end_str}")] = True
                t += timedelta(minutes=15)

available_slots = []
for (date_str, time_range) in available.keys():
    time_str = time_range.split('-')[0]
    minute = int(time_str.split(':')[1])
    if minute % 30 == 0:
        if time_range not in [str(v) for v in st.session_state.booked_global.values()] and is_slot_available(date_str, time_range, st.session_state.booked_global):
            slot_key = str((date_str, time_range))
            if slot_key not in st.session_state.booked_global:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                day_name = ["週一", "週二", "週三", "週四", "週五"][date_obj.weekday()]
                available_slots.append({
                    "display": f"{date_str} ({day_name}) {time_range}",
                    "date": date_str,
                    "time": time_range
                })

if st.session_state.confirmed:
    # ========== 預約成功頁面 ==========
    date_str, time_range = st.session_state.confirmed_info
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    day_name = ["週一", "週二", "週三", "週四", "週五"][date_obj.weekday()]

    st.success("✅ 面試預約已完美確認！")
    st.info(f"📅 時間：{date_str} ({day_name}) {time_range}")
    if st.session_state.meet_link:
        st.info(f"🔗 Google Meet 線上會議室：{st.session_state.meet_link}")
    st.info("面試確認信與日曆邀請已同步發送至您的信箱。若需更改時間，請聯繫招募團隊。")
    st.balloons()  

else:
    # ========== 時段選擇頁面 ==========
    st.markdown("### 📝 應徵者身分登錄")
    
    default_name = st.query_params.get("name", "")
    default_email = st.query_params.get("email", "")

    col1, col2 = st.columns(2)
    with col1:
        applicant_name = st.text_input("請輸入您的真實姓名（需與履歷相同）", value=default_name, placeholder="例如：陳小明")
    with col2:
        applicant_email = st.text_input("請輸入您的電子信箱（需與履歷相同）", value=default_email, placeholder="例如：xxxxx@gmail.com")
    
    st.divider()
    st.markdown("### 📅 請選擇一個您有空的面試時段")

    if available_slots:
        by_date = {}
        for slot in available_slots:
            date = slot["date"]
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(slot)

        for date_str in sorted(by_date.keys()):
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            day_name = ["週一", "週二", "週三", "週四", "週五"][date_obj.weekday()]
            st.markdown(f"**📅 {date_str} ({day_name})**")
            slots = by_date[date_str]
            cols = st.columns(4)

            for idx, slot in enumerate(slots):
                with cols[idx % 4]:
                    is_selected = st.session_state.selected_slot == (slot["date"], slot["time"])
                    if is_selected:
                        st.markdown(f"""
                            <div style="background-color: #FFD700; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; color: #333;">
                                ✨ {slot['time']}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        if st.button(f"⏰ {slot['time']}", key=f"slot_{slot['date']}_{slot['time']}", use_container_width=True):
                            st.session_state.selected_slot = (slot["date"], slot["time"])
                            st.rerun()
            st.write("")  

        # ========== 核心確認按鈕 ==========
        if st.session_state.selected_slot:
            st.divider()
            if st.button("確認預約", use_container_width=True, key="confirm_final"):
                
                if not applicant_name.strip() or not applicant_email.strip():
                    st.warning("⚠️ 請先在頁面最上方填寫您的「姓名」與「電子信箱」，才能完成預約！")
                else:
                    date_str, time_range = st.session_state.selected_slot
                    start_time, end_time = time_range.split('-')

                    st.info("🔄 正在驗證您的應徵者身分，請稍候...")
                    
                    try:
                        print(f"[系統日誌] 正在連線 Google Sheets 進行身分驗證...")
                        SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                        
                        # ==========================================
                        # 🌟 雲端地雷 3 解除：Google Sheets 動態驗證
                        # ==========================================
                        if "gcp_service_account" in st.secrets:
                            creds_info = json.loads(st.secrets["gcp_service_account"])
                            base_creds = Credentials.from_service_account_info(creds_info)
                        else:
                            base_creds = Credentials.from_service_account_file("creds.json")
                            
                        scoped_creds = base_creds.with_scopes(SCOPE)
                        gs_client = gspread.authorize(scoped_creds)
                        sheet = gs_client.open("HR後台_應徵者追蹤表").sheet1
                        
                        all_rows = sheet.get_all_values()
                        target_row_index = None
                        
                        for idx, row in enumerate(all_rows, start=1):
                            if len(row) >= 4 and row[2].strip() == applicant_name.strip() and row[3].strip() == applicant_email.strip():
                                target_row_index = idx
                                break
                        
                        if not target_row_index:
                            st.error("🛑 身分驗證失敗！在招募系統中找不到符合此姓名與信箱的應徵資料。請檢查是否輸入錯誤，或確保你已通過初篩並收到面試邀約信。")
                        else:
                            check_start_final = datetime.strptime(f"{date_str} {start_time}", '%Y-%m-%d %H:%M') - BUFFER
                            check_end_final = datetime.strptime(f"{date_str} {end_time}", '%Y-%m-%d %H:%M') + BUFFER
                            
                            if not is_slot_available(date_str, time_range, st.session_state.booked_global):
                                st.error("🛑 預約失敗！該面試時段已被其他應徵者搶先預約了。請重新選擇其他時段！")
                            elif is_busy(check_start_final, check_end_final, busy_times_global):
                                st.error("🛑 預約失敗！主管在該時段的行程發生異動。請重新選擇其他時段！")
                            else:
                                st.success("🎉 身分驗證成功且時段確認空閒！正在為您建立 Google Calendar 面試活動...")
                                
                                event_id, google_meet_url = create_interview_event(
                                    applicant_name, applicant_email, 
                                    date_str, start_time, end_time
                                )
                                
                                if event_id:
                                    slot_key = str((date_str, time_range))
                                    st.session_state.booked_global[slot_key] = applicant_name
                                    save_bookings(st.session_state.booked_global)

                                    sheet.update_cell(target_row_index, 1, "面試排程已確認")  
                                    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                                    sheet.update_cell(target_row_index, 9, current_time_str)
                                    sheet.update_cell(target_row_index, 10, f"{date_str} {start_time}") 
                                    sheet.update_cell(target_row_index, 11, google_meet_url) 
                                
                                    st.info("✉️ 正在向您的信箱發送面試確認通知信...")
                                    
                                    # ==========================================
                                    # 🌟 雲端地雷 2 解除：Email 帳密改走 Secrets
                                    # ==========================================
                                    try:
                                        SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
                                        GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]
                                        yag = yagmail.SMTP(user=SENDER_EMAIL, password=GMAIL_APP_PASSWORD)
                                        
                                        subject = f"【面試確認】商管程式設計 -「{applicant_name}」技術面試預約成功通知"
                                        body = f"""{applicant_name} 您好：

您已成功預約本公司的技術面試，以下為您的專屬面試詳細資訊，請務必留意並準時出席：

📅 面試日期：{date_str}
⏰ 面試時間：{start_time} ~ {end_time} (台灣時間 GMT+8)
💻 線上會議連結（Google Meet）：{google_meet_url}

💡 溫馨提示：
1. 面試當天請點擊上方 Google Meet 連結進入會議室，主管將在線上與您進行面談。
2. 建議您於面試前 5 分鐘測試您的麥克風、視訊鏡頭與網路連線品質，以利面試順利進行。

祝您面試順利！

商管程式設計股份有限公司 招募團隊 敬上
"""
                                        yag.send(to=applicant_email, subject=subject, contents=body)
                                    except Exception as email_err:
                                        st.warning(f"面試已成立，但確認信發送失敗：{email_err}")
                                    
                                    st.session_state.confirmed = True
                                    st.session_state.confirmed_info = (date_str, time_range)
                                    st.session_state.meet_link = google_meet_url
                                    st.rerun()  
                                else:
                                    st.error("發生了預期外的狀況，請稍後再試。")
                    except Exception as e:
                        st.error(f"發生了預期外的狀況，請稍後再試：{e}")

    else:
        st.info("近期面試排程較緊湊，目前可選時段皆額滿，請直接致電人資部預約面試：0911-111-111")