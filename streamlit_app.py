"""
人資面試排程系統 - Streamlit 前端 (2026 正式上線優化版)
包含：動態應徵者表單(支援URL自動帶入)、自動生成 Google Meet、即時防雙重預約、Google Sheets 雲端連動、yagmail 面試信發送、系統除錯日誌
"""

import streamlit as st
import json
import os
import gspread
import yagmail
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from calendar_sync import create_interview_event

# ==================== 🛠️ HRIS 核心環境參數設定區 ====================
# 👇 實際部署時，請將金鑰放入環境變數中。本地測試請填入您的帳密（切勿推上 GitHub！）
SENDER_EMAIL = "@gmail.com"  
GMAIL_APP_PASSWORD = "你的gmail應用程式金鑰"  
# =================================================================

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

script_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(script_dir, "calendar_output.json")

try:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"[系統日誌] 成功讀取 calendar_output.json，包含 {len(data)} 位主管行程。")
except FileNotFoundError:
    st.error("❌ 找不到 calendar_output.json，請先執行 Calendar Picker 獲取主管日曆")
    st.stop()

emails = list(data.keys())
if len(emails) < 2:
    st.error("❌ 日曆資料不足（至少需要 2 個主管）")
    st.stop()

person1 = data[emails[0]]  
person2 = data[emails[1]]  

# 組合兩人所有的忙碌行程，完美防禦跨日事件
busy_times_global = [(item["start"], item["end"]) for item in person1 + person2]

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

all_dates = set()
for person_busy in data.values():
    for item in person_busy:
        all_dates.add(datetime.fromisoformat(item["start"]).date())

available = {}
for date in sorted(all_dates):
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
    
    # 🌟 吸收優點一：從 URL 參數自動抓取姓名與信箱，無縫帶入表單預設值
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
                    
                    # 🌟 吸收優點二：加入終端機日誌追蹤，大幅提升除錯能力
                    print(f"\n=============================================")
                    print(f"[系統日誌] 收到預約請求！")
                    print(f"[系統日誌] 應徵者：{applicant_name} ({applicant_email})")
                    print(f"[系統日誌] 選擇時段：{date_str} {time_range}")
                    
                    try:
                        print(f"[系統日誌] 正在連線 Google Sheets 進行身分驗證...")
                        SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
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
                            print(f"[系統警告] 身分驗證失敗！試算表查無此人，已自動攔截預約。")
                            st.error("🛑 身分驗證失敗！在招募系統中找不到符合此姓名與信箱的應徵資料。請檢查是否輸入錯誤，或確保你已通過初篩並收到面試邀約信。")
                        
                        else:
                            print(f"[系統日誌] 驗證成功！該應徵者位於資料表第 {target_row_index} 行。")
                            
                            check_start_final = datetime.strptime(f"{date_str} {start_time}", '%Y-%m-%d %H:%M') - BUFFER
                            check_end_final = datetime.strptime(f"{date_str} {end_time}", '%Y-%m-%d %H:%M') + BUFFER
                            
                            if not is_slot_available(date_str, time_range, st.session_state.booked_global):
                                print(f"[系統警告] 時段攔截！該時段已被其他人搶先預約。")
                                st.error("🛑 預約失敗！該面試時段已被其他應徵者搶先預約了。請重新選擇其他時段！")
                            elif is_busy(check_start_final, check_end_final, busy_times_global):
                                print(f"[系統警告] 時段攔截！主管在該時段已有新行程覆蓋。")
                                st.error("🛑 預約失敗！主管在該時段的行程發生異動。請重新選擇其他時段！")
                            else:
                                st.success("🎉 身分驗證成功且時段確認空閒！正在為您建立 Google Calendar 面試活動...")
                                print(f"[系統日誌] 正在呼叫 calendar_sync.py 建立 Google 日曆行程...")
                                
                                event_id, google_meet_url = create_interview_event(
                                    applicant_name, applicant_email, 
                                    date_str, start_time, end_time
                                )
                                
                                if event_id:
                                    print(f"[系統日誌] 日曆行程建立成功！Meet 連結: {google_meet_url}")
                                    
                                    slot_key = str((date_str, time_range))
                                    st.session_state.booked_global[slot_key] = applicant_name
                                    save_bookings(st.session_state.booked_global)

                                    print(f"[系統日誌] 正在同步資料回 Google Sheets...")
                                    sheet.update_cell(target_row_index, 1, "面試排程已確認")  
                                    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                                    sheet.update_cell(target_row_index, 9, current_time_str)
                                    sheet.update_cell(target_row_index, 10, f"{date_str} {start_time}") 
                                    sheet.update_cell(target_row_index, 11, google_meet_url) 
                                
                                    st.info("✉️ 正在向您的信箱發送面試確認通知信...")
                                    
                                    if SENDER_EMAIL != "YOUR_EMAIL@gmail.com" and GMAIL_APP_PASSWORD != "YOUR_16_DIGIT_PASSWORD":
                                        print(f"[系統日誌] 正在呼叫 Yagmail 發送確認信給 {applicant_email}...")
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
                                        print(f"[系統日誌] 郵件發送完成！整個預約流程完美落幕。")
                                        print(f"=============================================\n")
                                    
                                    st.session_state.confirmed = True
                                    st.session_state.confirmed_info = (date_str, time_range)
                                    st.session_state.meet_link = google_meet_url
                                    st.rerun()  
                                else:
                                    print(f"[系統錯誤] 呼叫 Google Calendar API 失敗。")
                                    st.error("發生了預期外的狀況，請稍後再試。")
                    except Exception as e:
                        print(f"\n[系統崩潰] 預期外錯誤發生：{e}")
                        print(f"=============================================\n")
                        st.error("發生了預期外的狀況，請稍後再試。")

    else:
        st.info("近期面試排程較緊湊，目前可選時段皆額滿，請直接致電人資部預約面試：0911-111-111")
