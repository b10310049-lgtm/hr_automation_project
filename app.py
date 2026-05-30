"""
人資招募自動化系統 - Streamlit 企業級儀表板 (方案B: 網頁雙向同步版)
包含：職缺範本儲存與載入、JD 檔案上傳、AI 動態草擬規則、記憶體履歷上傳、主管網頁審核、雙向 Sheets 同步、郵件分流機、進階群像分析儀表板
"""

import streamlit as st
import os
import pdfplumber
import time
import json
import gspread
import httpx
import yagmail
import pandas as pd
import re
import base64  # 🌟 新增：用於將檔案編碼傳輸給 Apps Script
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from google import genai

# ==================== 🛠️ 核心環境設定與快取 ====================
st.set_page_config(page_title="HRIS 自動化招募戰情室", layout="wide", page_icon="👔")

UI_THEME = {
    'TITLE_COLOR': '#154360',
    'BG_COLOR': '#FDFDFD',
    'PRIMARY': '#154360',
    'SECONDARY': '#2E86C1',
    'DANGER': "#ABD6F4",
    'WARNING': "#75BDEE",
    'PIE_COLORS': ["#154360", "#22628D", "#4B7998", "#ABD6F4", "#D6EAF8"],
    'GRID_STYLE': '#F2F2F2',
    'SKILL_BAR_COLOR': '#2874A6'
}

st.markdown("""
    <style>
    .stButton > button { font-weight: bold; }
    .stDataFrame { border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
    GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]
except KeyError as e:
    st.error(f"❌ 缺少系統機密變數：{e}。請檢查 .streamlit/secrets.toml 檔案。")
    st.stop()

@st.cache_resource
def init_google_sheets():
    try:
        SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        if "gcp_service_account" in st.secrets:
            creds_info = json.loads(st.secrets["gcp_service_account"])
            creds_object = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
        else:
            creds_object = Credentials.from_service_account_file("creds.json", scopes=SCOPE)
            
        gs_client = gspread.authorize(creds_object)
        return gs_client.open("HR後台_應徵者追蹤表").sheet1
    except Exception as e:
        st.error(f"❌ 雲端試算表連線失敗：{e}")
        return None

@st.cache_resource
def init_ai_client():
    try:
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"❌ AI 初始化失敗：{e}")
        return None

sheet = init_google_sheets()
client = init_ai_client()

# 初始化 session state
if "custom_rules" not in st.session_state:
    st.session_state.custom_rules = ""
if "current_job_title" not in st.session_state:
    st.session_state.current_job_title = ""
if "df_dash" not in st.session_state:
    st.session_state.df_dash = pd.DataFrame()

# ==================== 📂 職缺範本資料庫函數 ====================
PROFILE_FILE = "job_profiles.json"

def load_job_profiles():
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_job_profiles(profiles_dict):
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles_dict, f, ensure_ascii=False, indent=4)

# ==================== 🧠 核心功能函數 ====================

def generate_rules_from_jd(jd_text):
    prompt = f"""
    你是一位資深的科技業與獵頭招募專家。請根據以下【職缺說明(JD)】，列出 7 到 10 條最關鍵的「履歷評分與扣分/加分規則」。
    
    【格式嚴格要求】：
    1. 絕對不要使用 Markdown 的粗體雙星號 (**) 或斜體單星號 (*)。
    2. 每一行請統一使用半形圓點 (•) 作為開頭，後面接一個空格再開始寫文字。
    3. 直接條列輸出，不要有任何開場白或結語。
    
    【內容要求】：
    1. 必須包含針對「缺乏核心條件（如特定工具、學歷、年資）」的明確扣幾分建議。
    2. 必須包含針對「具備進階技能或特殊經歷」的明確加幾分建議。
    3. 若 JD 中有提到薪資範圍，請加入薪資不符的扣分規則。
    4. 必須在最後保留一條系統規則：「• Email 擷取：請極度精準擷取真實信箱，絕不修改拼寫。」
    
    【職缺說明(JD)】:
    {jd_text}
    """
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        clean_text = response.text.strip().replace("**", "")
        return clean_text
    except Exception as e:
        return f"⚠️ 規則生成失敗：{e}"

def upload_file_and_get_link(file_path, file_name):
    """透過 Google Apps Script 代理上傳，完美避開服務帳號 0 Bytes 容量限制"""
    try:
        # 1. 讀取 PDF 檔案並轉為 Base64 編碼，以利 JSON 傳輸
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            encoded_file = base64.b64encode(file_bytes).decode('utf-8')

        # ==========================================
        # 🚨 請將下方的網址換成你剛剛部署的 Web App URL
        # ==========================================
        WEB_APP_URL = "https://script.google.com/macros/s/AKfycby2aeYJ-fBoJ-Fc7RaeibP2fx83Jg9nvh27ABvDDx2x-I0QFaLt4m2oRi4ZYFs6CGDp/exec"

        payload = {
            "fileName": file_name,
            "mimeType": "application/pdf",
            "fileData": encoded_file
        }

        # 3. 發送 JSON POST 請求給你的專屬機器人
        response = httpx.post(WEB_APP_URL, json=payload, timeout=60.0, follow_redirects=True)

        if response.status_code == 200 and "Error" not in response.text:
            # 成功回傳永久連結
            return response.text.strip()
        else:
            st.error(f"❌ 代理上傳回傳錯誤：{response.text}")
            return "https://drive.google.com/resume/upload_failed"

    except Exception as e:
        st.error(f"❌ 代理上傳失敗：{e}")
        return "https://drive.google.com/resume/upload_failed"

def score_resume(file_name, resume_text, jd_text, rules_text, target_job_title):
    current_now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt = f"""
    你是一位極度嚴格的科技公司 HR 招募主管。請根據以下【職缺說明】與【應徵者履歷】，進行客觀評分與資料萃取。
    
    【目標職缺名稱】: {target_job_title}
    
    【職缺說明】: 
    {jd_text}
    
    【應徵者履歷】: 
    {resume_text}
    
    【自訂評分嚴格度與扣分規則指引】：
    {rules_text}
    
    【⚠️ 嚴格評分運算邏輯 (極度重要)】：
    1. 評分預設基準分數為 70 分（而非 100 分）。
    2. 請嚴格檢視履歷內容，逐條比對上方的「扣分規則」與「加分規則」，執行真實的數學加減法。
    3. 若應徵者的【期待薪資】明確高於 JD 預算或超出合理範圍，必須強制執行扣分，絕不能給滿分。
    4. 你必須在 JSON 內的 "score_calculation" 欄位寫下具體的「加減分算式過程」，最後才給出最終 "score"（最高 100 分）。
    
    請嚴格回覆以下 JSON，不要包含 Markdown tags：
    {{
        "status": "依分數決定：小於60填『AI評分完畢待發感謝信』，大於等於60填『AI評分完畢待主管審核』",
        "job_applied": "{target_job_title}",
        "name": "應徵者姓名",
        "email": "從履歷中擷取的信箱",
        "score_calculation": "評分運算過程，例如：基準70分 + 具備Python加10分 - 薪資超標扣15分 = 65分",
        "score": 分數數字,
        "applied_at": "{current_now_str}",
        "action_at": "{current_now_str}",
        "interview_at": "",
        "meeting_link": "",
        "highest_education": "高中職、學士、碩士、博士",
        "total_experience_years": 總年資數字,
        "expected_salary": 期待月薪數字,
        "skills_extracted": "技能標籤",
        "score_reason": "給分原因短評 (30-50字，須包含薪資是否超標的評估)",
        "resume": "網址佔位符"
    }}
    """
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text, True
    except Exception as e:
        return str(e), False

def write_to_google_sheet(data_dict, real_resume_url):
    if sheet is None: return "🛑 試算表未連線"
    try:
        target_job = data_dict.get("job_applied", "").strip()
        target_email = data_dict.get("email", "").strip()
        candidate_name = data_dict.get("name", "")
        score = data_dict.get("score", 0)
        
        all_jobs = sheet.col_values(2)
        all_emails = sheet.col_values(4)
        existing_records = set(zip(all_jobs, all_emails))
        
        if (target_job, target_email) in existing_records:
            return f"🛑 攔截重複投遞：{candidate_name} ({target_email}) 已存在於試算表，拒絕重複寫入。"
            
        final_status = "AI評分完畢待發感謝信" if score < 60 else "AI評分完畢待主管審核"
        next_row = len(all_jobs) + 1
        
        front_part = [final_status, target_job, candidate_name, target_email, score]
        back_part = [
            data_dict.get("applied_at", ""), data_dict.get("action_at", ""), 
            "", "", data_dict.get("highest_education", ""), 
            data_dict.get("total_experience_years", 0), data_dict.get("expected_salary", 0), 
            data_dict.get("skills_extracted", ""), data_dict.get("score_reason", ""), real_resume_url
        ]
        
        sheet.update(f"A{next_row}:E{next_row}", [front_part])
        sheet.update(f"H{next_row}:Q{next_row}", [back_part])
        return f"🚀 {candidate_name} 寫入成功！職缺：【{target_job}】/ 狀態：【{final_status}】"
        
    except Exception as e:
        return f"❌ 寫入雲端表格時發生致命錯誤：{e}"

# ==================== 🖥️ Streamlit 網頁介面 ====================

st.title("👔 HRIS 企業招募戰情室")
tab1, tab2, tab3, tab4 = st.tabs(["📥 AI 履歷解析", "👨‍💼 主管審核區", "📬 郵件分流台", "📊 群像分析與決策儀表板"])

# ---------------------------------------------------------
# Tab 1: AI 履歷解析中心
# ---------------------------------------------------------
with tab1:
    st.header("📥 AI 履歷解析中心")
    
    if "current_job_title" not in st.session_state: st.session_state.current_job_title = ""
    if "current_jd" not in st.session_state: st.session_state.current_jd = ""
    if "custom_rules" not in st.session_state: st.session_state.custom_rules = ""
    
    job_profiles = load_job_profiles()
    job_profile_names = list(job_profiles.keys())
    
    def on_profile_change():
        selected = st.session_state.profile_selector
        if selected == "➕ 手動新增職缺":
            st.session_state.current_job_title = ""
            st.session_state.current_jd = ""
            st.session_state.custom_rules = ""
        else:
            st.session_state.current_job_title = selected
            st.session_state.current_jd = job_profiles[selected].get("jd", "")
            st.session_state.custom_rules = job_profiles[selected].get("rules", "")

    st.markdown("### 🎯 設定目前招募職缺")
    st.selectbox("📂 載入已儲存的職缺範本：", ["➕ 手動新增職缺"] + job_profile_names, key="profile_selector", on_change=on_profile_change)
    st.text_input("請輸入您目前正在招募的職缺名稱：", key="current_job_title")
    
    with st.expander("📝 編輯職缺條件 (JD) 與 AI 評估規則", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📄 1. 職缺說明 (JD)")
            jd_file = st.file_uploader("上傳 JD PDF 檔進行文字萃取 (選填)", type=["pdf"], key="jd_upload")
            
            if jd_file:
                try:
                    with pdfplumber.open(jd_file) as pdf:
                        extracted = "".join([p.extract_text() for p in pdf.pages])
                        if extracted != st.session_state.current_jd:
                            st.session_state.current_jd = extracted
                            st.rerun()
                except Exception as e:
                    st.error(f"❌ 讀取 JD 檔案失敗：{e}")
                    
            st.text_area("請在此確認或修改目前的 JD 內容：", key="current_jd", height=350)
            
            if st.button("✨ 讓 AI 根據 JD 自動草擬 7-10 條評分規則", use_container_width=True):
                if st.session_state.current_jd.strip():
                    with st.spinner("AI 正在分析 JD 關鍵字與篩選條件..."):
                        new_rules = generate_rules_from_jd(st.session_state.current_jd)
                        st.session_state.custom_rules = new_rules
                        st.rerun() 
                else:
                    st.warning("請先上傳或填寫 JD 內容！")
            
        with col2:
            st.markdown("### ⚖️ 2. AI 評分與扣分規則")
            st.caption("您可以手動輸入，或點擊左側按鈕讓 AI 自動草擬乾淨格式。")
            st.text_area("請在此輸入您的評估與扣分邏輯：", key="custom_rules", height=415)
            
        st.write("")
        if st.button("💾 一鍵儲存此職缺設定 (包含 JD 與評分規則)", type="secondary", use_container_width=True):
            job_name = st.session_state.current_job_title.strip()
            if not job_name:
                st.error("⚠️ 請先在上方填寫「職缺名稱」才能進行儲存！")
            else:
                job_profiles[job_name] = {
                    "jd": st.session_state.current_jd,
                    "rules": st.session_state.custom_rules
                }
                save_job_profiles(job_profiles)
                st.success(f"✅ 成功將 JD 與評估規則儲存至「{job_name}」專屬範本中！下次可直接從下拉選單載入。")

    st.divider()
    uploaded_files = st.file_uploader("📥 上傳應徵者履歷 (支援多選)", type=["pdf"], accept_multiple_files=True)
    
    if st.button("🚀 開始 AI 智慧評估", type="primary", use_container_width=True):
        if not uploaded_files:
            st.warning("⚠️ 請先上傳至少一份履歷！")
        elif not st.session_state.current_jd.strip() or not st.session_state.custom_rules.strip() or not st.session_state.current_job_title.strip():
            st.warning("⚠️ 職缺名稱、JD 與評分規則不得為空！")
        else:
            with st.status("🤖 AI 面試官啟動中...", expanded=True) as status:
                for file in uploaded_files:
                    st.write(f"正在處理：{file.name}...")
                    
                    temp_path = f"temp_{file.name}"
                    with open(temp_path, "wb") as f:
                        f.write(file.getbuffer())
                    
                    # 使用更新後的代理機器人上傳函數
                    real_url = upload_file_and_get_link(temp_path, file.name)
                    
                    with pdfplumber.open(temp_path) as pdf:
                        full_text = "".join([p.extract_text() for p in pdf.pages])
                    
                    st.write(f"🧠 AI 正在深度分析 {file.name} ...")
                    
                    result_json, is_ok = score_resume(file.name, full_text, st.session_state.current_jd, st.session_state.custom_rules, st.session_state.current_job_title)
                    
                    if is_ok:
                        try:
                            match = re.search(r'\{[\s\S]*\}', result_json)
                            clean_json = match.group(0) if match else result_json
                            
                            data_dict = json.loads(clean_json)
                            msg = write_to_google_sheet(data_dict, real_url)
                            
                            if "❌" in msg or "🛑" in msg:
                                st.warning(msg)
                            else:
                                st.success(msg)
                                
                        except json.JSONDecodeError:
                            st.error(f"❌ {file.name} 的 AI 回傳格式損壞。")
                            with st.expander("🔍 查看錯誤回傳內容"):
                                st.code(result_json)
                    else:
                        st.error(f"❌ {file.name} 評估失敗：{result_json}")
                        
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
                status.update(label="✅ 所有履歷評估完成！", state="complete", expanded=False)
            st.balloons()

# ---------------------------------------------------------
# Tab 2: 主管審核區
# ---------------------------------------------------------
with tab2:
    st.header("👨‍💼 主管審核看板")
    st.info("💡 **審核規則說明**：\n\nAI 評分 60 分以上的履歷會由主管手動勾選是否邀約面試。若決定邀約請「打勾」；若評估後認為條件不符，請「保持不勾選，並務必在評語區寫下原因」，供 HR 後續進行漏斗分析與調整招募策略。")
    
    if sheet:
        all_rows = sheet.get_all_values()
        if len(all_rows) > 1:
            all_job_titles = sorted(list(set([row[1].strip() for row in all_rows[1:] if len(row) > 1 and row[1].strip() != ""])))
            
            if not all_job_titles:
                st.success("🎉 目前試算表中沒有任何資料。")
            else:
                col_filter, col_btn = st.columns([3, 1])
                with col_filter:
                    selected_job_tab2 = st.selectbox("🎯 請選擇要審核的職缺：", ["顯示全部職缺"] + all_job_titles, key="filter_tab2")
                with col_btn:
                    st.write("")
                    st.write("")
                    if st.button("🔄 重新載入名單", key="reload_sheet_tab2"):
                        st.rerun()

                review_data = []
                for idx, row in enumerate(all_rows[1:], start=2):
                    row = row + [""] * (17 - len(row))
                    job_title_in_sheet = row[1].strip()
                    
                    is_status_match = (row[0].strip() == "AI評分完畢待主管審核")
                    is_job_match = (selected_job_tab2 == "顯示全部職缺" or selected_job_tab2 == job_title_in_sheet)
                    
                    if is_status_match and is_job_match:
                        review_data.append({
                            "Sheet_Row": idx,
                            "應徵職缺": job_title_in_sheet,
                            "姓名": row[2],
                            "AI 分數": int(row[4]) if row[4].isdigit() else 0,
                            "AI 評分原因": row[15],
                            "✅ 核准面試": row[5].strip().upper() == "TRUE",
                            "📝 主管評語": row[6],
                            "履歷連結": row[16]
                        })
                
                if review_data:
                    df = pd.DataFrame(review_data)
                    
                    edited_df = st.data_editor(
                        df,
                        column_config={
                            "Sheet_Row": None, 
                            "履歷連結": st.column_config.LinkColumn("履歷連結", display_text="點我觀看履歷"),
                            "✅ 核准面試": st.column_config.CheckboxColumn("✅ 核准面試", default=False),
                            "AI 評分原因": st.column_config.TextColumn("AI 評分原因 (點擊查看)", width="large")
                        },
                        disabled=["應徵職缺", "姓名", "AI 分數", "AI 評分原因", "履歷連結"],
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    if st.button("💾 儲存主管審核結果並同步至雲端", type="primary"):
                        with st.spinner("正在將主管的決定同步至 Google Sheets..."):
                            update_count = 0
                            for i in range(len(df)):
                                original_approved = df.iloc[i]["✅ 核准面試"]
                                edited_approved = edited_df.iloc[i]["✅ 核准面試"]
                                original_comment = df.iloc[i]["📝 主管評語"]
                                edited_comment = edited_df.iloc[i]["📝 主管評語"]
                                
                                if original_approved != edited_approved or original_comment != edited_comment:
                                    row_idx = edited_df.iloc[i]["Sheet_Row"]
                                    sheet.update_cell(row_idx, 6, str(edited_approved).upper())
                                    sheet.update_cell(row_idx, 7, edited_comment)
                                    update_count += 1
                                    
                            if update_count > 0:
                                st.success(f"✅ 成功同步 {update_count} 筆主管審核結果！請前往「郵件分流台」發送通知信。")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.info("無任何變更需要儲存。")
                else:
                    st.info(f"👉 在「{selected_job_tab2}」這個分類下，目前沒有需要主管審核的履歷。")
        else:
            st.success("🎉 目前沒有需要主管審核的履歷。")

# ---------------------------------------------------------
# Tab 3: 郵件分流台
# ---------------------------------------------------------
with tab3:
    st.header("📬 自動郵件分流台")
    
    if sheet:
        all_rows = sheet.get_all_values()
        
        if len(all_rows) > 1:
            all_job_titles_tab3 = sorted(list(set([row[1].strip() for row in all_rows[1:] if len(row) > 1 and row[1].strip() != ""])))
            
            col_filter3, col_empty = st.columns([3, 1])
            with col_filter3:
                selected_job_tab3 = st.selectbox("🎯 請選擇要檢視或發送信件的職缺：", ["顯示全部職缺"] + all_job_titles_tab3, key="filter_tab3")
                
            current_time = datetime.now()
            names_reject = []          
            names_pending_invite = []   
            names_manager_reject = []   
            
            for row in all_rows[1:]:
                row = row + [""] * (17 - len(row))
                status = row[0].strip()
                job_title = row[1].strip()
                name = row[2].strip()
                score = int(row[4]) if row[4].isdigit() else 0
                manager_approve_str = row[5].strip().upper()
                manager_comment = row[6].strip()
                applied_at_str = row[7].strip()
                
                if selected_job_tab3 != "顯示全部職缺" and job_title != selected_job_tab3:
                    continue
                
                if status == "AI評分完畢待發感謝信" and score < 60:
                    time_info = " (時間解過失敗)"
                    try:
                        applied_time = datetime.strptime(applied_at_str, "%Y-%m-%d %H:%M")
                        target_send_time = applied_time + timedelta(days=2)
                        time_diff = target_send_time - current_time
                        
                        if time_diff.total_seconds() <= 0:
                            time_info = " 🔴 (已屆滿 48 小時，點擊按鈕將立即發信)"
                        else:
                            days = time_diff.days
                            hours = time_diff.seconds // 3600
                            if days > 0:
                                time_info = f" ⏳ (還剩 {days} 天 {hours} 小時發信)"
                            else:
                                time_info = f" ⏳ (還剩 {hours} 小時發信)"
                    except:
                        pass
                    names_reject.append(f"• {name} {time_info} [應徵: {job_title}]")
                    
                elif status == "AI評分完畢待主管審核" and score >= 60 and manager_approve_str == "TRUE":
                    names_pending_invite.append(f"• {name} [應徵: {job_title}]")
                    
                elif status == "AI評分完畢待主管審核" and score >= 60 and manager_approve_str == "FALSE" and manager_comment != "":
                    names_manager_reject.append(f"• {name} [應徵: {job_title}]")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("即將發送：AI 淘汰感謝信", len(names_reject))
            col2.metric("即將發送：主管核准面邀信", len(names_pending_invite))
            col3.metric("即將發送：主管拒絕的感謝信", len(names_manager_reject))
            
            st.write("")
            col1_list, col2_list, col3_list = st.columns(3)
            with col1_list:
                st.markdown("**📄 預計寄送之應徵者名單：**")
                if names_reject:
                    for n in names_reject: st.write(n)
                else:
                    st.caption("目前無待處理名單")
                    
            with col2_list:
                st.markdown("**📄 預計寄送之應徵者名單：**")
                if names_pending_invite:
                    for n in names_pending_invite: st.write(n)
                else:
                    st.caption("目前無待處理名單")
                    
            with col3_list:
                st.markdown("**📄 預計寄送之應徵者名單：**")
                if names_manager_reject:
                    for n in names_manager_reject: st.write(n)
                else:
                    st.caption("目前無待處理名單")
                    
            st.divider()

            if st.button(f"⚡ 啟動郵件狀態機 (派發「{selected_job_tab3}」的信件)", type="primary", use_container_width=True):
                if not SENDER_EMAIL or GMAIL_APP_PASSWORD == "YOUR_16_DIGIT_PASSWORD":
                    st.error("⚠️ 未設定真實的寄信憑證，無法執行郵件發送。")
                else:
                    with st.status("📬 郵件派發引擎運轉中...", expanded=True) as log_status:
                        try:
                            yag = yagmail.SMTP(user=SENDER_EMAIL, password=GMAIL_APP_PASSWORD)
                            trigger_count = 0
                            
                            for idx, row in enumerate(all_rows[1:], start=2):
                                row = row + [""] * (17 - len(row))
                                status = row[0].strip()
                                job_title = row[1].strip()
                                name = row[2].strip()
                                email = row[3].strip()
                                score = int(row[4]) if row[4].isdigit() else 0
                                manager_approve_str = row[5].strip().upper()
                                manager_comment = row[6].strip()
                                applied_at_str = row[7].strip()
                                
                                if selected_job_tab3 != "顯示全部職缺" and job_title != selected_job_tab3:
                                    continue
                                
                                if status not in ["AI評分完畢待主管審核", "AI評分完畢待發感謝信"]:
                                    continue
                                    
                                if score < 60:
                                    try:
                                        applied_time = datetime.strptime(applied_at_str, "%Y-%m-%d %H:%M")
                                        is_past_two_days = current_time >= (applied_time + timedelta(days=2))
                                    except Exception:
                                        is_past_two_days = False

                                    if is_past_two_days:
                                        st.write(f"⚡ [快車道自動攔截] 向 {name} 發送感謝信...")
                                        subject = f"【商管程式設計】應徵職缺「{job_title}」階段性結果通知"
                                        body = f"{name} 您好：\n感謝您對本公司「{job_title}」職缺的關注。經初步評估後，由於本次應徵者眾多，您的背景與目前團隊所需的特定技術框架在匹配度上稍有落差，本次暫時無法安排下一階段的面試流程。祝您未來職涯發展順利，也期待日後有機會合作！\n\n商管程式設計股份有限公司 招募團隊 敬上"
                                        yag.send(to=email, subject=subject, contents=body)
                                        
                                        sheet.update_cell(idx, 1, "已發感謝信")
                                        sheet.update_cell(idx, 9, current_time.strftime("%Y-%m-%d %H:%M"))
                                        trigger_count += 1
                                        time.sleep(1)
                                        
                                elif score >= 60 and manager_approve_str == "TRUE":
                                    st.write(f"🚀 [主管核准] 正在向 {name} 發送面試邀約...")
                                    subject = f"【面試邀約】商管程式設計 -「{job_title}」團隊面試邀請"
                                    # 🌟 已經更新為真實前台網址
                                    booking_url = f"https://ntupbc-interview-booking.streamlit.app/?name={name}&email={email}"
                                    body = f"""{name} 您好：<br><br>
感謝您投遞本公司的「{job_title}」職缺。經主管深入評估您的專業背景與履歷後，我們誠摯地邀請您參與下一階段的線上面試！<br><br>
為了配合技術主管的公務檔期，我們安排了線上預約系統，顯示主管未來三週的所有空閒時段，已即時同步更新至下方網頁中。<br><br>
👇【請點擊下方連結進入系統，自主挑選「一個空檔時段」預約您的面試時間】：<br>
<a href="{booking_url}" style="font-size: 16px; font-weight: bold; color: #1a73e8;">點擊此處前往面試預約系統</a><br><br>
<span style="color: gray; font-size: 12px;">
💡 溫馨提示：為避免熱門時段被其他優秀應徵者搶先鎖定，建議您於收到本信件 24 小時內完成預約。預約成功後將即時發送面試信件至您的信箱，再請查收，期待與您相見！<br><br>
商管程式設計股份有限公司 招募團隊 敬上
"""
                                    yag.send(to=email, subject=subject, contents=body)
                                    sheet.update_cell(idx, 1, "已發面邀未回覆") 
                                    sheet.update_cell(idx, 9, current_time.strftime("%Y-%m-%d %H:%M"))
                                    trigger_count += 1
                                    time.sleep(1)
                                    
                                elif score >= 60 and manager_approve_str == "FALSE" and manager_comment != "":
                                    st.write(f"📝 [主管拒絕] 正在向 {name} 發送感謝信...")
                                    subject = f"【商管程式設計】應徵職缺「{job_title}」階段性結果通知"
                                    body = f"{name} 您好：\n感謝您投遞本公司的「{job_title}」職缺。您的履歷硬實力非常優秀，然而經用人主管評估後，認為目前您在技術框架或是薪資期待上和本職缺的匹配度稍有落差，因此本次暫時無法為您安排面試。再次感謝您的投遞，也期待未來有機會與您合作！\n\n商管程式設計股份有限公司 招募團隊 敬上"
                                    yag.send(to=email, subject=subject, contents=body)
                                    
                                    sheet.update_cell(idx, 1, "已發感謝信")
                                    sheet.update_cell(idx, 9, current_time.strftime("%Y-%m-%d %H:%M"))
                                    trigger_count += 1
                                    time.sleep(1)
                                    
                            log_status.update(label=f"🎉 執行完畢！共實質發送 {trigger_count} 封郵件。", state="complete", expanded=True)
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 郵件發送引擎崩潰：{e}")
        else:
            st.info("系統目前沒有資料可以寄發信件。")

# ---------------------------------------------------------
# Tab 4: 商業決策儀表板 (進階洞察分析)
# ---------------------------------------------------------
with tab4:
    st.header("📊 群像分析與招募商業決策報告")
    
    col_dash_load, col_dash_empty = st.columns([1, 3])
    with col_dash_load:
        if st.button("🔄 同步雲端數據並載入分析", type="primary"):
            with st.spinner("正在從 Google Sheets 抓取最新數據..."):
                if sheet:
                    raw_vals = sheet.get_all_values()
                    if len(raw_vals) > 1:
                        st.session_state.df_dash = pd.DataFrame(raw_vals[1:], columns=raw_vals[0])
                        st.success("✅ 數據同步完成！")
                    else:
                        st.warning("目前試算表中沒有招募資料。")
                else:
                    st.error("🛑 試算表未連線")
    
    if not st.session_state.df_dash.empty:
        df_dash = st.session_state.df_dash.copy()
        
        # 🌟 強效資料清洗
        df_dash = df_dash[df_dash['name'].astype(str).str.strip() != ""]
        
        if not df_dash.empty:
            df_dash['expected_salary'] = df_dash['expected_salary'].astype(str).str.replace(r'[^\d.]', '', regex=True)
            df_dash['expected_salary'] = pd.to_numeric(df_dash['expected_salary'], errors='coerce')
            df_dash['total_experience_years'] = df_dash['total_experience_years'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
            df_dash['score'] = pd.to_numeric(df_dash['score'], errors='coerce')
            df_dash['applied_at'] = pd.to_datetime(df_dash['applied_at'], errors='coerce')

            st.divider()
            
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                dash_job_list = ["全部"] + list(df_dash['job_applied'].dropna().unique())
                sel_dash_job = st.selectbox("🎯 篩選分析職缺", dash_job_list)
            with c_f2:
                sel_dash_time = st.radio("⏰ 時間維度", ["全部", "近一週", "近三週"], horizontal=True)

            if sel_dash_job != "全部":
                df_dash = df_dash[df_dash['job_applied'] == sel_dash_job]
            
            now_t = pd.Timestamp.now()
            if sel_dash_time == "近一週":
                df_dash = df_dash[df_dash['applied_at'] >= (now_t - pd.Timedelta(days=7))]
            elif sel_dash_time == "近三週":
                df_dash = df_dash[df_dash['applied_at'] >= (now_t - pd.Timedelta(days=21))]

            if not df_dash.empty:
                # 🏆 核心 KPI 漏斗
                t_app = len(df_dash)
                invited_st = ['已發面邀未回覆', '已發面邀', '面試排程已確認', '已錄取']
                t_inv = len(df_dash[df_dash['status'].isin(invited_st)])
                t_hire = len(df_dash[df_dash['status'] == '已錄取'])
                
                ck1, ck2, ck3 = st.columns(3)
                ck1.metric("👥 總應徵", f"{t_app} 人")
                ck2.metric("✉️ 進入面試階段", f"{t_inv} 人", f"總轉換率: {int(t_inv/t_app*100) if t_app>0 else 0}%")
                ck3.metric("🎉 最終錄取", f"{t_hire} 人", f"錄取率: {int(t_hire/t_app*100) if t_app>0 else 0}%")

                st.divider()

                # ================= 決策圖表 1 & 2 =================
                col_c1, col_c2 = st.columns(2)

                with col_c1:
                    # 🚀 升級一：各年資階段面試轉換率 (雙軸圖)
                    def seg_exp(y):
                        if pd.isna(y): return '未知'
                        if y <= 2: return '0-2年'
                        elif y <= 5: return '3-5年'
                        else: return '5年以上'
                    df_dash['年資分組'] = df_dash['total_experience_years'].apply(seg_exp)
                    df_dash['is_invited'] = df_dash['status'].isin(invited_st)
                    
                    exp_groups = ['0-2年', '3-5年', '5年以上']
                    exp_df = df_dash.groupby('年資分組')['is_invited'].agg(['count', 'sum']).reindex(exp_groups).fillna(0)
                    exp_df['rate'] = (exp_df['sum'] / exp_df['count'] * 100).fillna(0).round(1)

                    fig_exp = make_subplots(specs=[[{"secondary_y": True}]])
                    fig_exp.add_trace(go.Bar(
                        x=exp_df.index, y=exp_df['count'], name="投遞人數", marker_color=UI_THEME['PRIMARY']
                    ), secondary_y=False)
                    fig_exp.add_trace(go.Scatter(
                        x=exp_df.index, y=exp_df['rate'], name="面試轉換率 (%)", mode='lines+markers',
                        marker=dict(size=10, color=UI_THEME['WARNING']), line=dict(width=3)
                    ), secondary_y=True)

                    fig_exp.update_layout(title="<b>各年資階段投遞人數與面試轉換率</b>", plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    fig_exp.update_yaxes(title_text="應徵人數", secondary_y=False)
                    fig_exp.update_yaxes(title_text="轉換率 (%)", secondary_y=True, range=[0, max(100, exp_df['rate'].max()+10)])
                    st.plotly_chart(fig_exp, use_container_width=True)

                with col_c2:
                    # 🚀 升級二：淘汰死因分析 (甜甜圈圖)
                    df_rej = df_dash[~df_dash['status'].isin(invited_st)].copy()
                    
                    def categorize_reason(row):
                        if pd.notna(row['manager_comment']) and row['manager_comment'].strip() != "":
                            comment = str(row['manager_comment']).strip()
                            if any(k in comment for k in ['預算', '薪資', '薪水', '貴', '核薪', '高']): return '主管: 預算/薪資不符'
                            return '主管: 其他條件不符'
                        else:
                            reason = str(row['score_reason'])
                            if any(k in reason for k in ['預算', '薪資', '薪水', '貴', '超標', '高']): return 'AI: 薪資預期過高'
                            if any(k in reason for k in ['經驗', '無', '缺乏', '不符', '單薄', '白紙', '不熟', '不足']): return 'AI: 技能/經驗不足'
                            return 'AI: 其他條件不符'
                            
                    if not df_rej.empty:
                        df_rej['fail_reason'] = df_rej.apply(categorize_reason, axis=1)
                        reason_counts = df_rej['fail_reason'].value_counts()
                        
                        fig_reason = go.Figure(data=[go.Pie(
                            labels=reason_counts.index, values=reason_counts.values, hole=.5,
                            marker=dict(colors=[UI_THEME['DANGER'], UI_THEME['SECONDARY'], UI_THEME['WARNING'], UI_THEME['PRIMARY']]),
                            textinfo='label+percent', textposition='outside'
                        )])
                        fig_reason.update_layout(title="<b>招募漏斗淘汰原因分析</b>", showlegend=False)
                        st.plotly_chart(fig_reason, use_container_width=True)
                    else:
                        st.info("尚無淘汰數據可供分析。")

                st.divider()

                # ================= 決策圖表 3 & 4 =================
                col_c3, col_c4 = st.columns(2)

                with col_c3:
                    # 🚀 經典保留：評分與期待薪資散佈圖
                    fig_scatter = go.Figure()
                    fig_scatter.add_trace(go.Scatter(
                        x=df_dash['score'], y=df_dash['expected_salary'], mode='markers', text=df_dash['name'],
                        marker=dict(size=12, color=UI_THEME['SECONDARY'], opacity=0.7, line=dict(width=1, color='white')),
                        hovertemplate="<b>%{text}</b><br>AI評分: %{x}分<br>期待薪資: %{y:,.0f}元<extra></extra>"
                    ))
                    fig_scatter.update_layout(title="<b> AI 評分 vs 期待薪資散布圖</b>", plot_bgcolor='rgba(0,0,0,0)', xaxis_title="AI 綜合評分 (0-100)", yaxis_title="期待薪資 (TWD)")
                    st.plotly_chart(fig_scatter, use_container_width=True)

                with col_c4:
                    # 🚀 升級三：技能溢價分析 (雙軸圖)
                    df_s = df_dash[['name', 'expected_salary', 'skills_extracted']].copy()
                    df_s['skills_extracted'] = df_s['skills_extracted'].astype(str).str.split(',')
                    df_exp = df_s.explode('skills_extracted')
                    df_exp['skills_extracted'] = df_exp['skills_extracted'].str.strip().str.upper()
                    df_exp = df_exp[df_exp['skills_extracted'] != ""]
                    
                    skill_agg = df_exp.groupby('skills_extracted').agg(
                        Count=('name', 'count'),
                        AvgSalary=('expected_salary', 'mean')
                    ).reset_index()
                    
                    # 取前 10 大熱門技能
                    top_skills = skill_agg.sort_values('Count', ascending=False).head(10)
                    
                    fig_skills = make_subplots(specs=[[{"secondary_y": True}]])
                    fig_skills.add_trace(go.Bar(
                        x=top_skills['skills_extracted'], y=top_skills['Count'], name="具備人數", marker_color=UI_THEME['SKILL_BAR_COLOR']
                    ), secondary_y=False)
                    fig_skills.add_trace(go.Scatter(
                        x=top_skills['skills_extracted'], y=top_skills['AvgSalary'], name="平均期待薪資", mode='lines+markers',
                        marker=dict(size=10, color=UI_THEME['WARNING']), line=dict(width=3)
                    ), secondary_y=True)

                    fig_skills.update_layout(title="<b>核心技能價格分析</b>", plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    fig_skills.update_yaxes(title_text="具備此技能人數", secondary_y=False)
                    fig_skills.update_yaxes(title_text="該技能群體平均期待薪資 (TWD)", secondary_y=True)
                    st.plotly_chart(fig_skills, use_container_width=True)

            else:
                st.warning("此篩選條件下無符合的應徵者資料。")
    else:
        st.info("👈 請點擊左上方的「同步雲端數據並載入分析」按鈕，以取得最新的招募儀表板報表。")