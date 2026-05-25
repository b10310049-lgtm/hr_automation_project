"""
人資面試排程系統 - 最終版

功能：
1. 讀取兩個主管的Google日曆忙碌時段
2. 計算兩人都有空的時段
3. 生成可供應聘者選擇的面試時間（每個時段1小時，每15分鐘一個選項）
4. 支援應聘者線上預約

核心邏輯：
- 面試時間：1小時
- 緩衝時間：前後各15分鐘（確保主管有準備和結束時間）
- 驗證：申請時間 + 前後15分鐘都要主管空閒，且完全在工作時間內
"""

import json
import os
from datetime import datetime, timedelta

# 【新增】導入 Google Calendar 同步模組
from calendar_sync import create_interview_event

# ========== 設定 ==========
WORK_SESSIONS = [(9, 12), (13, 18)]  # 工作時間：早上9-12點，下午13-18點（24小時制）
BUFFER = timedelta(minutes=15)  # 面試前後各保留15分鐘的緩衝時間（供主管準備和結束）
INTERVIEW_LEN = timedelta(hours=1)  # 每場面試持續1小時

# ========== 讀取日曆檔案 ==========
# Calendar_FreeTime_Picker.py 會生成 calendar_output.json
# 格式：{email: [{start: "2026-05-18T09:00:00", end: "2026-05-18T10:00:00", timezone: "GMT+8"}, ...]}
# 其中存的是各人的「忙碌時段」（不是空閒時段）

script_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(script_dir, "calendar_output.json")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 70)
print("【人資面試排程系統】")
print("=" * 70)

# 提取兩個主管的資料
emails = list(data.keys())
person1 = data[emails[0]]  # 第一個主管的忙碌時段列表
person2 = data[emails[1]]  # 第二個主管的忙碌時段列表
print(f"\n✓ 已讀取：{emails[0]} 和 {emails[1]}")

# ========== 計算所有可用時段 ==========

def is_busy(check_start, check_end, busy_list):
    """
    檢查某個時間段是否與主管的忙碌時段有衝突

    參數：
    - check_start: 要檢查的開始時間（datetime物件）
    - check_end: 要檢查的結束時間（datetime物件）
    - busy_list: 忙碌時段列表，每項格式 (start_str, end_str)

    返回：
    - True: 有衝突（無法預約）
    - False: 無衝突（可以預約）

    邏輯：兩個時間段無重疊的充要條件是：
    check_end <= busy_start OR check_start >= busy_end
    如果不滿足此條件，則存在重疊
    """
    for busy_start_str, busy_end_str in busy_list:
        busy_start = datetime.fromisoformat(busy_start_str)
        busy_end = datetime.fromisoformat(busy_end_str)
        # 檢查是否有時間重疊
        if not (check_end <= busy_start or check_start >= busy_end):
            return True  # 有衝突
    return False  # 無衝突

# 【第1步】提取日曆中的所有日期
all_dates = set()
for person_busy in data.values():
    for item in person_busy:
        all_dates.add(datetime.fromisoformat(item["start"]).date())

available = {}  # 可預約時段的字典 {(日期str, 時間str): True}

# 【第2步】逐日掃描，計算可預約的面試時間
for date in sorted(all_dates):
    # 只考慮平日（0=週一 ... 4=週五，5=週六，6=週日）
    if date.weekday() < 5:
        # 提取這一天兩位主管各自的忙碌時段
        busy1 = [item for item in person1 if datetime.fromisoformat(item["start"]).date() == date]
        busy2 = [item for item in person2 if datetime.fromisoformat(item["start"]).date() == date]

        # 【關鍵】合併兩人的忙碌時段
        # 只有兩人都空閒的時段才能預約
        busy_times = [(item["start"], item["end"]) for item in busy1 + busy2]

        # 【第3步】對每個工作時段進行掃描
        for work_start, work_end in WORK_SESSIONS:
            # 建立該工作時段的時間邊界
            ws = datetime.combine(date, datetime.min.time().replace(hour=work_start))
            we = datetime.combine(date, datetime.min.time().replace(hour=work_end))

            # 【掃描範圍的計算】
            # scan_start = 工作開始 + 15分鐘（確保前面有緩衝）
            # scan_end = 工作結束 - 1小時 - 15分鐘（確保後面有足夠空間）
            # 例如：9:00-12:00 → 掃描 9:15-10:45
            scan_start = ws + BUFFER
            scan_end = we - INTERVIEW_LEN - BUFFER

            # 【第4步】逐15分鐘掃描（每15分鐘產生一個面試選項）
            t = scan_start
            while t <= scan_end:
                # 【驗證邏輯】
                # 申請時間：t 到 t+1小時
                # 需驗證：(t-15分鐘) 到 (t+1小時+15分鐘) 都要主管空閒
                check_start = t - BUFFER
                check_end = t + INTERVIEW_LEN + BUFFER

                # 檢查這個時段是否可用
                if not is_busy(check_start, check_end, busy_times):
                    # 可用！記錄這個時間選項
                    date_str = date.strftime('%Y-%m-%d')
                    time_str = t.strftime('%H:%M')
                    end_str = (t + INTERVIEW_LEN).strftime('%H:%M')
                    available[(date_str, f"{time_str}-{end_str}")] = True

                # 移動到下一個15分鐘的檢查點
                t += timedelta(minutes=15)

print(f"✓ 共 {len(available)} 個可用時段\n")

# ========== 【第5步】顯示所有可用時段 ==========
# 將計算結果按日期分組，方便應聘者查看

print("=" * 70)
print("📅 所有可選時段：")
print("=" * 70)

# 按日期重新組織資料，方便顯示
by_date = {}
for (date_str, time_str) in available.keys():
    if date_str not in by_date:
        by_date[date_str] = []
    by_date[date_str].append(time_str)

# 顯示每一天的可預約時段
for date_str in sorted(by_date.keys()):
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    day_name = ["週一", "週二", "週三", "週四", "週五"][date_obj.weekday()]
    print(f"\n📆 {date_str} ({day_name})")
    print("-" * 70)
    for time_str in sorted(by_date[date_str]):  # 按時間排序
        print(f"   {time_str}")

print("\n" + "=" * 70)

# ========== 【第6步】應聘者預約 ==========
# 接收應聘者的預約輸入

booked = {}  # 預約記錄 {(date_str, time_str): 應聘者名字}

print("\n【預約】輸入格式：名字 日期 時間（如：Amy 2026-05-18 10:15-11:15）")
print("輸入「done」結束\n")

while True:
    line = input("預約: ").strip()

    # 允許多種方式結束輸入
    if line.lower() in ["done", "結束", "q"]:
        break

    # 忽略空白行
    if not line:
        continue

    # 【寬容的格式解析】允許多個空格
    parts = line.split()

    # 檢查輸入的元素個數
    if len(parts) < 3:
        print("❌ 請輸入：名字 日期 時間（例如：Amy 2026-05-18 10:15-11:15）\n")
        continue

    # 提取三個主要元素
    name = parts[0]        # 應聘者名字
    date_str = parts[1]    # 日期 (格式：2026-05-18)
    time_str = parts[2]    # 時間 (格式：10:15-11:15)

    # 【驗證1】檢查日期格式是否正確
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        print("❌ 日期格式錯誤（應為 2026-05-18）\n")
        continue

    # 【驗證2】檢查時間格式是否正確（應包含一個"-"分隔符）
    if "-" not in time_str or time_str.count("-") != 1:
        print("❌ 時間格式錯誤（應為 10:15-11:15）\n")
        continue

    # 【驗證3】檢查該時段是否在可選時段中
    if (date_str, time_str) not in available:
        print(f"❌ {date_str} {time_str} 不在可選時段\n")
        continue

    # 【驗證4】檢查該時段是否已被其他人預約
    if (date_str, time_str) in booked:
        print(f"❌ 已被預約\n")
        continue

    # 【驗證5】檢查與已預約時段的緩衝衝突（新增）
    # 新申請的時間 + 前後15分鐘 不能與已預約時段 + 前後15分鐘 重疊
    time_parts = time_str.split('-')
    new_start_time = datetime.strptime(f"{date_str} {time_parts[0]}", '%Y-%m-%d %H:%M')
    new_end_time = datetime.strptime(f"{date_str} {time_parts[1]}", '%Y-%m-%d %H:%M')

    new_required_start = new_start_time - timedelta(minutes=15)
    new_required_end = new_end_time + timedelta(minutes=15)

    # 檢查是否與已預約的面試衝突
    has_buffer_conflict = False
    for (booked_date, booked_time), _ in booked.items():
        if booked_date == date_str:  # 同一天
            booked_parts = booked_time.split('-')
            booked_start = datetime.strptime(f"{booked_date} {booked_parts[0]}", '%Y-%m-%d %H:%M')
            booked_end = datetime.strptime(f"{booked_date} {booked_parts[1]}", '%Y-%m-%d %H:%M')

            booked_required_start = booked_start - timedelta(minutes=15)
            booked_required_end = booked_end + timedelta(minutes=15)

            # 檢查是否有時間重疊
            if not (new_required_end <= booked_required_start or new_required_start >= booked_required_end):
                has_buffer_conflict = True
                break

    if has_buffer_conflict:
        print(f"❌ 已被預約\n")
        continue

    # 【預約成功】記錄預約資訊
    booked[(date_str, time_str)] = name

    # 獲取週幾的名稱，用於顯示
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    day_name = ["週一", "週二", "週三", "週四", "週五"][date_obj.weekday()]

    # 顯示預約成功的訊息
    print(f"✅ {name} 預約 {date_str} ({day_name}) {time_str}")

    # 【新增】自動同步到 Google Calendar
    print("   正在建立 Google Calendar 事件...")
    event_id = create_interview_event(name, date_str, time_str)
    if event_id:
        print(f"   ✓ 已通知主管（Google Calendar 邀請已發送）\n")
    else:
        print(f"   ⚠️ Google Calendar 同步失敗（但預約已記錄）\n")

# ========== 【第7步】顯示最終結果 ==========
# 統計和顯示所有預約結果

print("\n" + "=" * 70)
print("【預約結果】")
print("=" * 70)

if booked:
    # 按日期時間排序顯示所有預約
    for (date_str, time_str), name in sorted(booked.items()):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        day_name = ["週一", "週二", "週三", "週四", "週五"][date_obj.weekday()]
        print(f"{name:10s} {date_str} ({day_name}) {time_str}")
    print(f"\n✓ 共 {len(booked)} 人預約")
else:
    print("無預約")

# 顯示還有多少個時段未被預約
print(f"📝 還有 {len(available) - len(booked)} 個時段可用")
print("=" * 70)