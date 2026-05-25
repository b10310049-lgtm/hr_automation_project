# 人資面試排程系統 (NTU PBC HR Interview Scheduling System)

## 🌐 線上試用

👉 **[點擊這裡試用系統](https://interview-scheduling-system.streamlit.app)**

> ⚠️ 線上版本為演示用途，可查看可用時段。Google Calendar 同步功能需要本地部署並配置 Google OAuth 凭證。詳見 [部署指南](DEPLOYMENT_GUIDE.md)。

---

## 📋 專案概述

一個完整的 HR 面試排程解決方案，整合 Google Calendar、智能算法和 Streamlit 前端，自動化管理主管檔期和應聘者預約流程。

### 核心功能
- ✅ 自動讀取主管 Google Calendar 忙碌時段
- ✅ 智能計算可用面試時段（1小時/場，15分鐘緩衝）
- ✅ 應聘者線上選擇面試時間
- ✅ 自動建立 Google Calendar 邀請並通知主管
- ✅ 防止雙重預約，確保時段衝突檢測
- ✅ 持久化預約記錄

---

## 📁 專案結構

```
期末專案/
├── Calendar_FreeTime_Picker.py      # 獲取主管日曆忙碌時段
├── project演算法_最終版.py          # 核心排程算法
├── calendar_sync.py                  # Google Calendar 事件建立模組
├── streamlit_app.py                  # 應聘者預約前端
├── clear_calendar_events.py          # 測試工具：批量清除日曆事件
├── credentials.json                  # Google OAuth 身分證（需自行配置）
├── token.json                        # Google 授權通行證（自動生成）
├── calendar_output.json              # 主管忙碌時段資料（自動生成）
├── bookings.json                     # 預約記錄（自動生成）
└── README.md                         # 本檔案
```

---

## 🚀 快速開始

### 1️⃣ 環境準備

#### 安裝依賴
```bash
pip install streamlit google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

#### 配置 Google API
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案
3. 啟用 **Google Calendar API**
4. 建立 **OAuth 2.0 客戶端 ID**（應用程式類型：桌面應用程式）
5. 下載 JSON 金鑰，保存為 `credentials.json` 到本目錄

### 2️⃣ 工作流程

#### 步驟 1：獲取主管日曆
```bash
python Calendar_FreeTime_Picker.py
```
- 首次執行會開啟瀏覽器進行 Google OAuth 認證
- 自動查詢兩位主管未來 3 週的忙碌時段
- 輸出結果到 `calendar_output.json`

#### 步驟 2：啟動應聘者預約系統
```bash
streamlit run streamlit_app.py
```
- 瀏覽器自動打開 `http://localhost:8501`
- 應聘者選擇可用時段進行預約
- 預約成功後自動建立 Google Calendar 邀請

#### 步驟 3（可選）：命令行版本算法演示
```bash
python project演算法_最終版.py
```
- 純命令行介面，用於測試或批量處理
- 讀取 `calendar_output.json`
- 手動輸入應聘者名字和選擇時間

---

## 🔧 各模組詳解

### `Calendar_FreeTime_Picker.py`
**功能**：自動獲取主管日曆資訊

**輸入**：
- `target_emails`: 主管 Google 帳號列表

**處理過程**：
1. 呼叫 Google Calendar API（`events().list()`）
2. 篩選已確認的忙碌事件
3. 轉換 UTC 時間 → 台灣時間（GMT+8）
4. 排除週末（只保留週一至週五）

**輸出**：`calendar_output.json`
```json
{
  "b10310038@g.ntu.edu.tw": [
    {
      "start": "2026-05-20T14:00:00",
      "end": "2026-05-20T15:00:00",
      "timezone": "GMT+8"
    }
  ],
  "b10310049@g.ntu.edu.tw": [...]
}
```

### `project演算法_最終版.py`
**功能**：計算可預約的面試時段

**核心邏輯**：
1. **掃描日期**：遍歷所有工作日
2. **掃描時間**：15分鐘間隔掃描（9:00-12:00 和 13:00-18:00）
3. **驗證可用性**：
   - ✅ 申請時間 + 前後各15分鐘都要主管空閒
   - ✅ 必須在工作時間內
   - ✅ 不能與已預約時段衝突（含緩衝區）

**時段篩選**：
- 只顯示30分鐘倍數的時段（如 10:00、10:30、11:00）
- 實際掃描仍是15分鐘間隔，但展示給使用者時過濾

### `calendar_sync.py`
**功能**：建立 Google Calendar 邀請事件

**函數**：
- `create_interview_event(applicant_name, date_str, time_range)`
  - 建立面試事件
  - 邀請兩位主管
  - 設定30分鐘提醒
  - 返回事件 ID

- `delete_interview_event(event_id)`
  - 刪除指定事件（取消預約時使用）

### `streamlit_app.py`
**功能**：應聘者線上預約前端

**UI 元素**：
- 📅 按日期分組顯示可用時段
- ⏰ 時間方塊（點擊選擇）
- ✨ 金色高亮（已選擇）
- ✅ 確認預約按鈕

**技術細節**：
- 使用 Streamlit Session State 管理狀態
- JSON 檔案持久化預約記錄
- 自動衝突檢測（新預約 vs 既有預約 + 緩衝區）

### `clear_calendar_events.py`（測試工具）
**功能**：批量刪除 Google Calendar 上的所有面試事件

**使用**：
```bash
python clear_calendar_events.py
```
- 搜尋所有標題含「【面試】」的事件
- 列出後要求確認
- 輸入 `yes` 確認刪除

---

## 📊 時間計算邏輯

### 工作時間設定
```
上午：09:00 - 12:00
下午：13:00 - 18:00
```

### 緩衝時間
```
每場面試 1 小時
前後各預留 15 分鐘緩衝
→ 實際佔用時間 = 申請時間 ± 15 分鐘
```

### 例子
如果應聘者選擇 **10:15-11:15**：
- 申請面試時間：10:15 ~ 11:15
- 實際預留時間：10:00 ~ 11:30
- 這段時間內主管不能有其他會議

---

## 🔐 資料儲存

| 檔案 | 內容 | 自動生成 |
|------|------|---------|
| `credentials.json` | Google OAuth 身分證 | ❌ 需手動配置 |
| `token.json` | 授權通行證 | ✅ 首次認證後自動生成 |
| `calendar_output.json` | 主管忙碌時段 | ✅ 執行 Picker 後生成 |
| `bookings.json` | 預約記錄 | ✅ Streamlit 預約後生成 |

---

## ⚙️ 組員接手指南

### 新組員上手步驟
1. Clone 本倉庫
2. 在 Google Cloud Console 建立自己的 OAuth 金鑰（`credentials.json`）
3. 安裝依賴：`pip install -r requirements.txt`
4. 依流程執行（Calendar Picker → Streamlit App）

### 修改 Google 帳號
編輯以下檔案中的帳號列表：
- `Calendar_FreeTime_Picker.py` 第 186 行
- `calendar_sync.py` 第 21-24 行

### 修改工作時間
編輯各檔案中的 `WORK_SESSIONS` 或 `WORK_START/END`：
- `project演算法_最終版.py` 第 24 行
- `streamlit_app.py` 第 29 行

### 修改緩衝時間
編輯 `BUFFER` 變數：
```python
BUFFER = timedelta(minutes=15)  # 改為其他分鐘數
```

---

## 🐛 常見問題

### Q: 執行時出現「找不到 credentials.json」
**A**：需要在 Google Cloud Console 建立 OAuth 金鑰，詳見「環境準備」段落

### Q: Google Calendar 邀請發不出去
**A**：檢查 `token.json` 是否有正確的 `calendar` 寫入權限。刪除 `token.json` 重新認證

### Q: 預約後沒有出現在 Google Calendar
**A**：檢查是否同時執行多個 Python 程序，可能導致認證衝突

### Q: 想清除測試時產生的日曆事件
**A**：執行 `python clear_calendar_events.py`

---

## 📝 開發筆記

### 關鍵設計決策

**1. 為什麼用 15 分鐘掃描但只顯示 30 分鐘倍數？**
- 15分鐘掃描提升精度，避免遺漏可用時段
- 30分鐘倍數的顯示習慣符合一般人類思維

**2. 為什麼要實作雙重衝突檢測？**
- 第一層：vs 主管忙碌時段（含緩衝）
- 第二層：vs 已預約的面試（含緩衝）
- 兩層都過才能預約

**3. 為什麼分離 calendar_sync.py？**
- 命令行版本可獨立運作
- 便於日後擴展（如整合其他日曆系統）
- 模組化設計便於測試

---

## 🎯 未來優化方向

- [ ] 支援多主管不同時區
- [ ] 應聘者郵件通知
- [ ] 預約修改/取消功能
- [ ] 預約統計儀表板
- [ ] 資料庫持久化（取代 JSON）
- [ ] 行動裝置友善設計

---

## 📞 技術支援

遇到問題？檢查清單：
1. Google API 是否已啟用？
2. `credentials.json` 是否正確配置？
3. 依賴套件是否已安裝？
4. 是否有網路連線可連接 Google API？

---

**最後更新**：2026-05-17  
**版本**：1.0  
**作者**：NTU PBC HR Project Team
