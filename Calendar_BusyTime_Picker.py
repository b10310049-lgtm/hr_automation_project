import datetime  # 處理日期與時間的標準函式庫，用來計算「未來三週」與「時區轉換」
import json      # 處理 JSON 格式資料的工具，用來將抓到的資料儲存成檔案給同學讀取
import os.path   # 處理檔案路徑的工具，用來檢查 token.json 檔案是否存在

# 以下四行是 Google 官方提供的 API 套件，必須透過 pip install 安裝
from google.auth.transport.requests import Request   # 用來發送更新憑證（Refresh Token）的請求
from google.oauth2.credentials import Credentials      # 用來管理與儲存已授權的憑證資訊
from google_auth_oauthlib.flow import InstalledAppFlow # 處理第一次執行程式時，開啟瀏覽器進行 OAuth 登入的流程
from googleapiclient.discovery import build             # 用來建立與 Google 各項服務（如日曆）連線的物件

# ================= 設定區 =================

# 🟢 修正：將權限從 readonly 放大至完整存取，確保後續 Streamlit 網頁能順利「寫入」並生成 Google Meet 連結
SCOPES = ['https://www.googleapis.com/auth/calendar']

# 🟢 修正：存放從 Google Cloud Console 下載的身分證檔案路徑，改為當前資料夾相對路徑
CLIENT_SECRETS_FILE = 'credentials.json'

# 🟢 修正：解放同學寫死的 D 槽路徑！將自動生成的「通行證」存檔路徑改為當前資料夾
TOKEN_PATH = 'token.json'

# 🟢 修正：解放同學寫死的 D 槽路徑！將產生的主管忙碌時段 JSON 檔案直接存在當前資料夾
OUTPUT_PATH = 'calendar_output.json'


# ==========================================

def get_calendar_service():
    """
    功能：自動處理 Google API 的身分驗證流程。
    1. 優先尋找現有的 token.json (舊門票) 以避免重複登入。
    2. 如果門票過期，嘗試自動續約 (Refresh)。
    3. 如果沒有門票或續約失敗，開啟瀏覽器讓使用者手動授權。
    回傳：一個已連線的 Google Calendar 服務物件 (service)，供後續抓取資料使用。
    """
    creds = None  # 初始化憑證變數，預設為空
    
    # 檢查電腦中是否已經存在先前儲存過的「授權門票」(token.json)
    if os.path.exists(TOKEN_PATH):
        # 如果檔案存在，就載入這張門票資訊到 creds 變數中
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
    # 如果找不到門票，或是門票已經失效（例如被撤銷權限）
    if not creds or not creds.valid:
        # 檢查門票是否只是「過期」但還有「自動續約憑證」(refresh_token)
        if creds and creds.expired and creds.refresh_token:
            # 發送請求給 Google，在背景偷偷換一張新的門票，不需要使用者再次登入
            creds.refresh(Request())
        else:
            # 如果連續約憑證都沒有（通常是第一次執行），則啟動正式的登入流程
            # 讀取 credentials.json (身分證) 來啟動 OAuth2 流程
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            # 開啟電腦預設瀏覽器，讓使用者點擊「允許」授權。port=0 表示隨機選擇可用的通訊埠
            creds = flow.run_local_server(port=0)
            
        # 將這次拿到的新門票（包含續約憑證）存入電腦中，下次執行時就能直接讀取
        with open(TOKEN_PATH, 'w') as token:
            # 將憑證物件轉換為 JSON 格式文字並寫入檔案
            token.write(creds.to_json())
            
    # 使用驗證完成的憑證 (creds)，正式建立與 Google Calendar 第 3 版 (v3) API 的連線
    return build('calendar', 'v3', credentials=creds)

def fetch_and_save_calendar_data(emails, days_range=21):
    """
    功能：
    1. 向 Google API 請求指定帳號的忙碌時段 (Free/Busy)。
    2. 將從 API 拿到的原始資料（UTC 時區）校正為台灣時間 (UTC+8)。
    3. 判斷校正後的日期是否為假日（週六、日），並予以剔除。
    4. 將最終結果存檔並回傳，方便演算法同學接手。
    
    參數：
    - emails: 要查詢的帳號列表 (list)。
    - days_range: 要查詢的時間長度 (預設為 3 週 / 21 天)。
    """
    # 呼叫剛才寫好的驗證函數，需要 Google 許可的事，它都負責。
    service = get_calendar_service()

    # 1. 定義抓取的時間範圍 (Google API 規定必須使用 UTC 時間)
    now_utc = datetime.datetime.utcnow() # 取得目前的世界協調時間 (UTC)
    future_utc = now_utc + datetime.timedelta(days=days_range) # 計算 21 天後的時間點
    
    # 將時間物件轉為 Google API 要求字串格式，結尾的 'Z' 代表 Zulu time (UTC)
    time_min = now_utc.isoformat() + 'Z'
    time_max = future_utc.isoformat() + 'Z'

    # 【改進】改用 events().list() API 而不是 freebusy()
    # 原因：freebusy() 只抓標記為「忙碌」的事件，會漏掉標記為「閒置」的事件
    # events().list() 會抓所有事件，不分忙碌狀態

    print(f"正在請求 {emails} 的日曆事件...")
    
    processed_data = {}  # 準備一個空的字典，用來存放處理完的乾淨資料
    tw_delta = datetime.timedelta(hours=8)  # 定義台灣時區偏差量：比世界時間快 8 小時

    # 開始對每個帳號進行資料清洗
    for email in emails:
        # 【改進】使用 events().list() API 查詢該帳號的所有事件
        # 原因：freebusy() 只抓忙碌事件，會漏掉標記為「閒置」的事件
        try:
            events_result = service.events().list(
                calendarId=email,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            raw_events = events_result.get('items', [])  # 取得事件列表
        except Exception as e:
            print(f"⚠️  無法存取 {email} 的日曆：{e}")
            raw_events = []

        filtered_busy = [] # 用來存放過濾後的非假日時段

        for event in raw_events:
            # 【過濾】只保留已確認的事件
            if event.get('status') != 'confirmed':
                continue

            # 【過濾】排除「空閒」狀態的事件 (transparency: 'opaque'=忙碌, 'transparent'=空閒)
            if event.get('transparency') == 'transparent':
                continue

            # 提取開始和結束時間
            start_str = event['start'].get('dateTime') or event['start'].get('date')
            end_str = event['end'].get('dateTime') or event['end'].get('date')

            if not start_str or not end_str:
                continue

            # 將 API 回傳的時間字串轉換為 Python 的 datetime 物件
            try:
                start_dt = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end_dt = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            except:
                continue

            # 2. 轉換為台灣時間（+08:00）
            # 如果已經有時區資訊，會自動轉換；如果沒有，假設為 UTC
            tw_tz = datetime.timezone(datetime.timedelta(hours=8))

            if start_dt.tzinfo is None:
                # 如果沒有時區資訊，假設為 UTC
                start_dt = start_dt.replace(tzinfo=datetime.timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=datetime.timezone.utc)

            # 轉換為台灣時間
            start_tw = start_dt.astimezone(tw_tz)
            end_tw = end_dt.astimezone(tw_tz)

            # 3. 排除六日邏輯 (weekday(): 0=週一, 4=週五, 5=週六, 6=週日)
            # 關鍵：必須使用台灣時間 start_tw 來判斷
            if start_tw.weekday() < 5:
                # 若為平日，則將結果轉換為易讀的字串格式存入列表
                filtered_busy.append({
                    "start": start_tw.strftime('%Y-%m-%dT%H:%M:%S'),
                    "end": end_tw.strftime('%Y-%m-%dT%H:%M:%S'),
                    "timezone": "GMT+8"
                })

        # 將該位使用者的過濾後列表存入總字典
        processed_data[email] = filtered_busy
        print(f"✓ {email}: 找到 {len(filtered_busy)} 個忙碌時段")

    # 4. 執行匯出 JSON：將處理後的結果儲存到硬碟中
    try:
        # 開啟指定路徑的檔案，使用 utf-8 編碼確保中文或其他字元不亂碼
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            # 將字典轉為 JSON 文字，縮排為 4 空格以方便閱讀 (indent=4)
            json.dump(processed_data, f, indent=4, ensure_ascii=False)
        print(f"✅ 成功！資料已轉換為台灣時間並排除六日，存入：{OUTPUT_PATH}")
    except Exception as e:
        # 捕捉檔案寫入時可能發生的錯誤 (如權限不足或路徑不存在)
        print(f"❌ 存檔失敗：{e}")

    return processed_data # 回傳最終結果供後續可能的程式邏輯使用


# 這個判斷式代表：只有當「直接執行」這個 .py 檔案時，下面的程式碼才會跑。
# 如果這份檔案未來被其他同學「匯入 (import)」去調用裡面的函數，這段測試代碼就不會執行。
if __name__ == '__main__':
    
    # 1. 定義要抓取的對象：
    # 在這裡填入你和你朋友（或主管A）的 NTU Google 帳號。
    # 如果未來要增加第 3 個人，直接在列表中加入字串即可。
    target_emails = ['b10310038@g.ntu.edu.tw', 'b10310049@g.ntu.edu.tw']
    
    # 2. 正式執行函數：
    # 呼叫剛才寫好的核心函數，並將上面設定的 Email 列表傳進去。
    # 執行完畢後，它會自動產出 JSON 檔，並把結果存入 final_result 變數中。
    final_result = fetch_and_save_calendar_data(target_emails)