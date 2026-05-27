import uuid
import json
import os
import streamlit as st
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def get_calendar_service():
    """優先讀取雲端 Secrets，找不到才讀本地 token.json"""
    if "google_calendar_token" in st.secrets:
        token_info = json.loads(st.secrets["google_calendar_token"])
        creds = Credentials.from_authorized_user_info(token_info)
    elif os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    else:
        raise Exception("❌ 找不到 Google Calendar 授權 Token！")
        
    return build('calendar', 'v3', credentials=creds)

def create_interview_event(applicant_name, applicant_email, date_str, start_time_str, end_time_str):
    """
    🟢 終極修正版：精確對齊 Google Meet 官方規範，徹底解決 400 Bad Request
    """
    try:
        service = get_calendar_service()
        
        clean_date = date_str.strip()
        clean_start = start_time_str.strip()
        clean_end = end_time_str.strip()
        
        start_iso = f"{clean_date}T{clean_start}:00"
        end_iso = f"{clean_date}T{clean_end}:00"
        
        print(f"📡 正在向 Google 提交標準時間：{start_iso} 至 {end_iso}")
        
        attendees = [
            {'email': 'b10310049@g.ntu.edu.tw'}, 
            {'email': 'b10310038@g.ntu.edu.tw'}, 
            {'email': applicant_email.strip()}    
        ]
        
        event_body = {
            'summary': f'【面試】商管程式設計 - {applicant_name.strip()} 先生/小姐',
            'description': f'商管程式設計股份有限公司 線上技術面試。\n應聘者：{applicant_name.strip()}\n信箱：{applicant_email.strip()}',
            'start': {'dateTime': start_iso, 'timeZone': 'Asia/Taipei'},
            'end': {'dateTime': end_iso, 'timeZone': 'Asia/Taipei'},
            'attendees': attendees,
            'conferenceData': {
                'createRequest': {
                    'requestId': f"meet-{uuid.uuid4().hex[:8]}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                }
            },
            'reminders': {
                'useDefault': False,
                'overrides': [{'method': 'popup', 'minutes': 30}],
            },
        }
        
        event = service.events().insert(
            calendarId='primary',
            body=event_body,
            conferenceDataVersion=1
        ).execute()
        
        meet_link = ""
        conference_data = event.get('conferenceData', {})
        entry_points = conference_data.get('entryPoints', [])
        for ep in entry_points:
            if ep.get('entryPointType') == 'video':
                meet_link = ep.get('uri', '')
                break
                
        if not meet_link and entry_points:
            meet_link = entry_points[0].get('uri', '')
            
        print(f"✅ Google Meet 連結生成成功：{meet_link}")
        return event.get('id'), meet_link

    except Exception as e:
        print(f"❌ 日曆模組內部發生錯誤：{e}")
        return None, None
