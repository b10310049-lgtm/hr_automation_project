"""
Google Calendar 清除工具 - 測試用程式

功能：搜尋並批量刪除 Google Calendar 上所有標題含「【面試】」的事件
使用場景：
- 測試期間需要清除大量面試事件
- 一鍵清除所有測試數據，無需手動逐個刪除
"""

import os
from datetime import datetime, timedelta, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ========== Google API 設定 ==========
# 🌟 修正：將原本的 Windows D 槽絕對路徑，改成適合 Mac 環境與 main.py 一致的相對路徑
SCOPES = ['https://www.googleapis.com/auth/calendar']
CLIENT_SECRETS_FILE = 'credentials.json'  # 確保此檔案跟 credentials.json 在同一個資料夾
TOKEN_PATH = 'token.json'

# ========== Google Calendar 認證函數 ==========
def get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

# ========== 清除面試事件函數 ==========
def clear_interview_events():
    try:
        service = get_calendar_service()

        # ========== 步驟 1：定義查詢時間範圍 ==========
        # 🌟 修正：將舊版 utcnow() 改為新版 timezone.utc，避免終端機噴出 Deprecation 警告
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        future = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat().replace('+00:00', 'Z')

        print("=" * 70)
        print("🔍 Google Calendar 面試事件清除工具")
        print("=" * 70)
        print(f"\n正在搜尋未來 90 天內的面試事件...")

        # ========== 步驟 2：呼叫 API 查詢事件 ==========
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=future,
            singleEvents=True,
            q='【面試】',  # 🌟 提示：系統會搜尋事件標題有包含「【面試】」這四個字的行程
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        # ========== 步驟 3：顯示查詢結果 ==========
        if not events:
            print("✅ 沒有找到任何面試事件，日曆非常乾淨！\n")
            return

        print(f"✅ 找到 {len(events)} 個相關的面試事件\n")

        # ========== 步驟 4：列出所有要刪除的事件 ==========
        print("=" * 70)
        print("要刪除的事件清單：")
        print("=" * 70)

        for i, event in enumerate(events, 1):
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"{i}. {event['summary']}")
            print(f"   時間：{start}")
            if 'description' in event:
                print(f"   說明：{event['description'][:50]}...")
            print()

        # ========== 步驟 5：確認刪除 ==========
        print("=" * 70)
        confirm = input("確認要刪除以上所有事件嗎？(輸入 yes 確認，其他任何鍵取消): ").strip().lower()

        if confirm != 'yes':
            print("\n❌ 取消刪除，未更動任何日曆事件。\n")
            return

        # ========== 步驟 6：逐個刪除事件 ==========
        print("\n🗑️  正在執行雲端刪除...\n")
        deleted_count = 0

        for event in events:
            try:
                service.events().delete(
                    calendarId='primary',
                    eventId=event['id']
                ).execute()

                deleted_count += 1
                print(f"   ✓ 已刪除: {event['summary']}")

            except Exception as e:
                print(f"   ❌ 無法刪除: {event['summary']} - 錯誤原因：{e}")

        # ========== 步驟 7：顯示最終結果 ==========
        print(f"\n🎉 執行完畢！成功清除 {deleted_count}/{len(events)} 個測試面試行程！")
        print("=" * 70)

    except Exception as e:
        print(f"❌ 出錯：{e}")

if __name__ == '__main__':
    clear_interview_events()
