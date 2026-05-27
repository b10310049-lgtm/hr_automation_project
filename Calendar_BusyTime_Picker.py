import datetime  
import json      
import os.path   
import streamlit as st

from google.auth.transport.requests import Request   
from google.oauth2.credentials import Credentials      
from google_auth_oauthlib.flow import InstalledAppFlow 
from googleapiclient.discovery import build             

# ================= 設定區 =================
SCOPES = ['https://www.googleapis.com/auth/calendar']
CLIENT_SECRETS_FILE = 'credentials.json'
TOKEN_PATH = 'token.json'
OUTPUT_PATH = 'calendar_output.json'
# ==========================================

def get_calendar_service():
    creds = None  
    
    # 優先讀取雲端 Secrets
    if "google_calendar_token" in st.secrets:
        token_info = json.loads(st.secrets["google_calendar_token"])
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    # 本地備援讀取
    elif os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # 雲端環境無法觸發瀏覽器登入，此處僅限本地開發時執行
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # 若在本地端執行，將刷新或新取得的憑證存下來
        if "google_calendar_token" not in st.secrets:
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
            
    return build('calendar', 'v3', credentials=creds)

def fetch_and_save_calendar_data(emails, days_range=21):
    service = get_calendar_service()

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    future_utc = now_utc + datetime.timedelta(days=days_range)
    time_min = now_utc.isoformat().replace('+00:00', 'Z')
    time_max = future_utc.isoformat().replace('+00:00', 'Z')

    print(f"正在向 Google 請求 {emails} 的日曆事件...")
    
    processed_data = {}  
    tw_tz = datetime.timezone(datetime.timedelta(hours=8))  

    for email in emails:
        try:
            events_result = service.events().list(
                calendarId=email,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            raw_events = events_result.get('items', [])
        except Exception as e:
            print(f"⚠️  無法存取 {email} 的日曆：{e}")
            raw_events = []

        filtered_busy = []

        for event in raw_events:
            if event.get('status') == 'cancelled':
                continue

            if event.get('transparency') == 'transparent':
                continue

            start_raw = event['start'].get('dateTime') or event['start'].get('date')
            end_raw = event['end'].get('dateTime') or event['end'].get('date')

            if not start_raw or not end_raw:
                continue

            try:
                if len(start_raw) == 10:  
                    start_tw = datetime.datetime.strptime(start_raw, "%Y-%m-%d").replace(tzinfo=tw_tz)
                    end_tw = datetime.datetime.strptime(end_raw, "%Y-%m-%d").replace(tzinfo=tw_tz)
                else:
                    start_dt = datetime.datetime.fromisoformat(start_raw.replace('Z', '+00:00'))
                    end_dt = datetime.datetime.fromisoformat(end_raw.replace('Z', '+00:00'))
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=datetime.timezone.utc)
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=datetime.timezone.utc)
                    start_tw = start_dt.astimezone(tw_tz)
                    end_tw = end_dt.astimezone(tw_tz)
            except Exception as e:
                continue

            filtered_busy.append({
                "start": start_tw.strftime('%Y-%m-%dT%H:%M:%S'),
                "end": end_tw.strftime('%Y-%m-%dT%H:%M:%S'),
                "timezone": "GMT+8"
            })

        processed_data[email] = filtered_busy
        print(f"✓ {email}: 找到 {len(filtered_busy)} 個忙碌時段")

    try:
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=4, ensure_ascii=False)
        print(f"✅ 成功！資料已轉換為台灣時間並無損封裝，存入：{OUTPUT_PATH}")
    except Exception as e:
        print(f"❌ 存檔失敗：{e}")

    return processed_data 

if __name__ == '__main__':
    target_emails = ['b10310038@g.ntu.edu.tw', 'b10310049@g.ntu.edu.tw']
    final_result = fetch_and_save_calendar_data(target_emails)