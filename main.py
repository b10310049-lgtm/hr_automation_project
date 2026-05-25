import os
import pdfplumber
import time
import json
import gspread
import httpx  
import yagmail  
from datetime import datetime, timedelta  
from google.oauth2.service_account import Credentials
from google import genai

# ==================== 🛠️ 核心環境參數設定區 ====================
# 👇 實際部署時，請將金鑰放入環境變數中。本地測試請在此填入您的 Key（切勿推上 GitHub）
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"  

SENDER_EMAIL = "YOUR_EMAIL@gmail.com"  
GMAIL_APP_PASSWORD = "YOUR_16_DIGIT_PASSWORD"  
# ==============================================================

# 1. 配置 Google Sheets 憑證與連線
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
sheet = None

try:
    creds_object = Credentials.from_service_account_file("creds.json", scopes=SCOPE)
    gs_client = gspread.authorize(creds_object)
    sheet = gs_client.open("HR後台_應徵者追蹤表").sheet1
except Exception as e:
    print(f"❌ 雲端連線失敗，請檢查 creds.json 與試算表設定：{e}")

# 2. 初始化 AI 面試官核心
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"❌ AI 初始化失敗：{e}")

def upload_file_and_get_link(file_path, file_name):
    """將 PDF 上傳至開放暫存空間"""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_name, f, 'application/pdf')}
            response = httpx.post('https://tmpfiles.org/api/v1/upload', files=files, timeout=30.0)
            
            if response.status_code == 200:
                res_json = response.json()
                raw_url = res_json['data']['url']
                direct_url = raw_url.replace('https://tmpfiles.org/', 'https://tmpfiles.org/dl/')
                return direct_url
            else:
                return "https://drive.google.com/resume/api_error_status"
    except Exception as e:
        print(f"⚠️ 履歷網址生成失敗，原因：{e}")
        return "https://drive.google.com/resume/upload_failed"

def get_jd_text():
    with open("jd.txt", "r", encoding="utf-8") as f:
        return f.read()

def score_resume(file_name, resume_text, jd_text):
    current_now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    prompt = f"""
    你是一位極度嚴格的科技公司 HR 招募主管。請根據以下【職缺說明】與【應徵者履歷】，進行客觀評分與資料萃取。
    【職缺說明】: {jd_text}
    【應徵者履歷】: {resume_text}
    
    【評分嚴格度與扣分權重指引（滿分 100 分）】：
    1. 核心框架一票否決：本職缺是「Web 後端工程師」。應徵者必須具備 Flask, FastAPI 或 Django 其中至少一種網頁框架開發經驗。若履歷中完全沒有提到任何 Web 框架或 RESTful API 開發經驗（例如純 Data Engineer），不論其學歷或 Python 多強，總分「最高不得超過 60 分」，並必須在評分原因中註明「缺乏網頁後端框架經驗」。
    2. 薪資預算嚴格度：職缺月薪上限為 NT$ 70,000。請比對應徵者的期望薪資，若期望薪資高於 70,000（例如 85,000），請直接在總分重扣 15 分，並在評分原因中註明「薪資預算不符」。
    3. 聯絡資訊擷取：請極度精準地抓取應徵者的 Email。有些應徵者為了測試系統，會在履歷中放自訂的常用個人信箱，請完整複製，絕對不要修改、拼錯或遺漏任何字元。
    
    請嚴格按照以下 JSON 格式回覆，不要包含 any markdown tags（如 ```json）或額外文字：
    {{
        "status": "依分數決定：小於60填『AI評分完畢待發感謝信』，大於等於60填『AI評分完畢待主管審核』",
        "job_applied": "Python 後端開發工程師",
        "name": "應徵者中文姓名，若無則英文",
        "email": "從履歷中擷取的真實電子信箱，請務必完整複製",
        "score": 最終計算出的整數分數,
        "applied_at": "{current_now_str}",
        "action_at": "{current_now_str}",
        "interview_at": "",
        "meeting_link": "",
        "highest_education": "僅從『高中職、學士、碩士、博士』挑選一個符合的萃取，無則留空",
        "total_experience_years": 數字小數，請從履歷推算總工作年資,
        "expected_salary": 整數數字，若履歷有寫月薪或年薪請換算，無資料則留 0,
        "skills_extracted": "核心技能標籤，用半形逗號隔開",
        "score_reason": "AI 給予這個分數的具體原因與短評（30-50字）",
        "resume": "[https://drive.google.com/resume/placeholder](https://drive.google.com/resume/placeholder)"
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text, True
    except Exception as e:
        print(f" (⚠️ AI 連線失敗，真實死因：{e}) ")
        return None, False

def write_to_google_sheet(result_json, real_resume_url, is_real_ai):
    if sheet is None or not is_real_ai:
        print("🛑 由於 AI 當前處於配額用盡狀態，系統拒絕將不真實的模擬數據寫入表格。")
        return

    try:
        data = json.loads(result_json)
        
        target_job = data.get("job_applied", "").strip()
        target_email = data.get("email", "").strip()
        candidate_name = data.get("name", "")
        score = data.get("score", 0)
        
        all_jobs = sheet.col_values(2)
        all_emails = sheet.col_values(4)
        existing_records = set(zip(all_jobs, all_emails))
        
        if (target_job, target_email) in existing_records:
            print(f"🛑 攔截重複投遞：應徵者 {candidate_name} ({target_email}) 之前已投遞過「{target_job}」，系統自動拒絕寫入。")
            return
            
        final_status = "AI評分完畢待發感謝信" if score < 60 else "AI評分完畢待主管審核"
        next_row = len(all_jobs) + 1
        
        front_part = [
            final_status,
            target_job,
            candidate_name,
            target_email,
            score
        ]
        
        back_part = [
            data.get("applied_at", ""),
            data.get("action_at", ""),
            data.get("interview_at", ""),
            data.get("meeting_link", ""),
            data.get("highest_education", ""),
            data.get("total_experience_years", 0.0),
            data.get("expected_salary", 0),
            data.get("skills_extracted", ""),
            data.get("score_reason", ""),
            real_resume_url
        ]
        
        sheet.update(range_name=f"A{next_row}:E{next_row}", values=[front_part])
        sheet.update(range_name=f"H{next_row}:Q{next_row}", values=[back_part])
        
        print(f"🚀 雲端資料同步成功：{candidate_name} 的資料已精確填入第 {next_row} 行，狀態為【{final_status}】！")
        
    except Exception as e:
        print(f"❌ 寫入雲端表格失敗：{e}")

def run_email_notification_triage():
    """獨立軌道：純粹掃描表格，觸發自動化郵件分流狀態機"""
    if not SENDER_EMAIL or GMAIL_APP_PASSWORD == "你的16位字元Gmail應用程式密碼":
        print("\n⚠️ 提示：未設定寄信憑證，跳過郵件分流階段。")
        return

    print("\n📬 [獨立軌道啟動] 正在強力掃描 Google Sheet 主管勾選狀態...")
    try:
        yag = yagmail.SMTP(user=SENDER_EMAIL, password=GMAIL_APP_PASSWORD)
        all_rows = sheet.get_all_values()
        if len(all_rows) <= 1:
            print("ℹ️ 表格無應徵者資料。")
            return

        current_time = datetime.now()
        trigger_count = 0  

        for idx, row in enumerate(all_rows[1:], start=2):
            if len(row) < 9: 
                continue

            status = row[0].strip()
            job_title = row[1].strip()
            name = row[2].strip()
            email = row[3].strip()
            
            try:
                score = int(row[4])
            except ValueError:
                score = 0
                
            manager_approve_str = str(row[5]).strip().upper()
            manager_comment = row[6].strip()
            applied_at_str = row[7].strip() 

            # 🌟 修正：精確對齊目前的兩種 AI 評分後狀態
            valid_statuses = ["AI評分完畢待主管審核", "AI評分完畢待發感謝信"]
            if status not in valid_statuses:
                continue

            # 1. 快車道：自動拒絕
            if score < 60:
                try:
                    applied_time = datetime.strptime(applied_at_str, "%Y-%m-%d %H:%M")
                    is_past_two_days = current_time >= (applied_time + timedelta(days=2))
                except Exception:
                    is_past_two_days = False

                if is_past_two_days:
                    print(f"⚡ [快車道自動攔截] 滿 48 小時，正在向 {name} 發送感謝信...")
                    subject = f"【商管程式設計】應徵職缺「{job_title}」階段性結果通知"
                    body = f"{name} 您好：\n感謝您對本公司「{job_title}」職缺的關注。經初步評估後，由於本次應徵者眾多，您的背景與目前團隊所需的特定技術框架在匹配度上稍有落差，本次暫時無法安排下一階段的面試流程。祝您未來職涯發展順利，也期待日後有機會合作！\n\n商管程式設計股份有限公司 招募團隊 敬上"
                    yag.send(to=email, subject=subject, contents=body)
                    
                    # 🌟 更新狀態與 action_at (第 9 欄 / I 欄)
                    sheet.update_cell(idx, 1, "已發感謝信")
                    sheet.update_cell(idx, 9, current_time.strftime("%Y-%m-%d %H:%M"))
                    
                    print(f"✅ {name} 狀態已變更為：已發感謝信，並更新異動時間")
                    trigger_count += 1
                    time.sleep(1.5)
                else:
                    print(f"⏳ {name} ({score}分)：時限未滿 2 天，繼續處於緩衝等待期。")

            # 2. 慢車道：人工核准 (score >= 60 且打勾 TRUE)
            elif score >= 60 and manager_approve_str == "TRUE":
                print(f"🚀 [慢車道主管核准] 偵測到 TRUE！正在向 {name} 發送面試邀約...")
                subject = f"【面試邀約】商管程式設計 -「{job_title}」團隊面試邀請"
                
                body = f"""{name} 您好：

感謝您投遞本公司的「{job_title}」職缺。經主管深入評估您的專業背景與履歷後，我們誠摯地邀請您參與下一階段的線上面試！

為了配合技術主管的公務檔期，我們安排了線上預約系統，顯示主管未來三週的所有空閒時段，已即時同步更新至下方網頁中。

👉【請點擊此處進入系統，自主挑選「一個空檔時段」預約您的面試時間】：
http://localhost:8501

💡 溫馨提示：為避免熱門時段被其他優秀應徵者搶先鎖定，建議您於收到本信件 24 小時內完成預約。預約成功後將即時發送面試信件至您的信箱，再請查收，期待與您相見！

商管程式設計股份有限公司 招募團隊 敬上
"""
                yag.send(to=email, subject=subject, contents=body)
                
                # 🌟 更新狀態與 action_at
                sheet.update_cell(idx, 1, "已發面邀未回覆") 
                sheet.update_cell(idx, 9, current_time.strftime("%Y-%m-%d %H:%M"))
                
                print(f"✅ {name} 狀態已變更為：已發面邀未回覆，並更新異動時間")
                trigger_count += 1
                time.sleep(1.5)

            # 3. 慢車道：人工拒絕 (score >= 60 且打勾 FALSE 且有評語)
            elif score >= 60 and manager_approve_str == "FALSE" and manager_comment != "":
                print(f"📝 [慢車道主管拒絕] 偵測到反饋！正在向 {name} 發送感謝信...")
                subject = f"【商管程式設計】應徵職缺「{job_title}」階段性結果通知"
                body = f"{name} 您好：\n感謝您投遞本公司的「{job_title}」職缺。您的履歷硬實力非常優秀，然而經用人主管評估後，認為目前您在技術框架或是薪資期待上和本職缺的匹配度較低，因此本次暫時無法為您安排面試。再次感謝您的投遞，也期待未來有機會與您合作！\n\n商管程式設計股份有限公司 招募團隊 敬上"
                yag.send(to=email, subject=subject, contents=body)
                
                # 🌟 更新狀態與 action_at
                sheet.update_cell(idx, 1, "已發感謝信")
                sheet.update_cell(idx, 9, current_time.strftime("%Y-%m-%d %H:%M"))
                
                print(f"✅ {name} 狀態已變更為：已發感謝信，並更新異動時間")
                trigger_count += 1
                time.sleep(1.5)

        print(f"🎉 郵件狀態機執行完畢，本輪實質寄出 {trigger_count} 封信件！")
    except Exception as e:
        print(f"❌ 郵件發送錯誤：{e}")

def process_new_resumes():
    """主提進榜軌道：讀取本地 PDF 並分析寫入"""
    print("\n📥 [AI 掃描啟動] 開始讀取並使用 AI 分析新履歷...")
    jd = get_jd_text()
    resume_folder = "resumes/"
    
    pdf_files = [f for f in os.listdir(resume_folder) if f.endswith('.pdf')]
    if not pdf_files:
        print("ℹ️ resumes/ 資料夾內目前沒有任何 PDF 檔案。")
        return
        
    for file_name in pdf_files:
        path = os.path.join(resume_folder, file_name)
        print(f"\n📤 正在將 {file_name} 上傳並生成臨時檢視網址...")
        real_resume_url = upload_file_and_get_link(path, file_name)
        
        with pdfplumber.open(path) as pdf:
            full_text = "".join([p.extract_text() for p in pdf.pages])
            print(f"📑 智慧型 AI 評估中：{file_name}...")
            
            result_json, is_real_ai = score_resume(file_name, full_text, jd)
            write_to_google_sheet(result_json, real_resume_url, is_real_ai)
            time.sleep(2)

def main():
    print("")
    print("--- 🤖 自動化招募分流核心 ---")
    print(" [1] 讀取新履歷（呼叫 AI 評分並新增至雲端試算表）")
    print(" [2] 純郵件分流大掃描（不呼叫 AI，純看主管在試算表上的變更寄信）")
    
    choice = input("\n👉 請輸入執行軌道代號 [1 或 2]: ").strip()
    
    if choice == "1":
        process_new_resumes()
        # 讀完履歷後，程式結束，不會自動去掃試算表發信。如果想要連貫動作，可以再選 2。
    elif choice == "2":
        run_email_notification_triage()
    else:
        print("❌ 輸入無效，程式終止。")

if __name__ == "__main__":
    main()