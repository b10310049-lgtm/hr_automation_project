這份檔案是你們整個專案的 **`README.md`（專案說明書 / 使用手冊）**。

客觀且誠實地告訴你：**這份檔案不僅絕對不能刪，它還是你 GitHub 倉庫裡最重要的一面「門面」！** 因為任何人（包含英國碩士的審查委員、教授）點進你的 GitHub 網頁時，GitHub 會自動把這份檔案渲染成你們專案的主頁。一份寫得詳細、專業的 `README.md`，能直接決定外人對你這個專案的第一技術印象。

針對這份說明書，我幫你進行了嚴謹的「產品經理級審查（PM Review）」。為了完美對齊我們這幾天對系統做出的**巨大升級（引入 AI 評分、最後異動時間、漏斗戰情室、已錄取狀態）**，這份 `README.md` **必須立刻進行大更新**，否則會跟你們現在強大的程式碼完全脫節。

以下是幫你全面翻新、注入 **AI（Gemini 2.5）與 People Analytics 靈魂** 的完整版 `README.md`。請直接全選並覆蓋你原本的檔案：

---

### 📝 翻新後的完整版 `README.md`（請全選複製）

```markdown
# 👔 組織行為與資料決策：AI 驅動型自動化 ATS 招募系統與人資排程戰情室
*(NTU PBC AI-Driven Applicant Tracking System & HR Analytics Dashboard)*

## 🌐 系統三大核心模組展示

本系統全面採取「前後端分離」與「雲端大腦」的企業級軟體架構建置，包含以下三大獨立運作之模組：

1. **🤖 AI 自動化招募大腦 (`main.py`)**：負責讀取應徵者 PDF 履歷、調用 **Gemini 2.5 Flash** 進行硬實力一票否決與薪資預算防呆評分，並觸發 48 小時自動化分流發信。
2. **📅 應徵者自主面試預約系統 (`streamlit_app.py`)**：[Port 8501] 自動串接主管 Google Calendar，計算 15 分鐘緩衝期之空檔，供高分候選人線上自主排程並動態生成 Google Meet 會議。
3. **📊 HR 招募決策戰情室 (`dashboard.py`)**：[Port 8502] 提供即時資料庫群像分析、**招募漏斗（Recruitment Funnel）轉換率**、以及市場核心技能供需排行地圖（Skills Inventory）。

---

## 📋 專案概述與商業價值

在現代人力資源管理（HRIS）與人才數據分析（People Analytics）中，招募漏斗的轉換效率與薪資市場定位是企業組織行為的核心決策依據。

本專案針對傳統招募痛點，開發出端到端的自動化流。透過將「薪資預算」與「核心技術框架」納入 AI 評分權重，並即時動態追蹤**求職者最後異動時間（`action_at`）**，協助企業高層一眼看出招募瓶頸（例如：薪資開太低導致優質即戰力嚴重流失），達成真正數據驅動（Data-Driven）的組織管理決策。

---

## 📁 完整專案結構


```

hr_automation_project/
├── main.py                          # 🤖 核心大腦：AI 履歷分析、評分與自動化郵件分流
├── streamlit_app.py                 # 📅 前端網頁：應徵者自主預約面試與 Meet 連結生成
├── dashboard.py                     # 📊 後台網頁：HR 招募戰情室、漏斗轉換率與技能橫條圖
├── calendar_picker.py               # 📡 背景服務：自動向 Google API 請求主管日曆 busy 區間
├── calendar_sync.py                 # 🔗 日曆模組：負責建立/刪除 Google Calendar 與 Meet 事件
├── calendar_clear.py                # 🧹 測試工具：資安防呆！一鍵批量清除日曆上所有測試面試
├── jd.txt                           # 📄 職缺說明：Python 後端開發工程師的必備與加分條件
├── resumes/                         # 📥 履歷資料夾：存放待分析的應徵者 PDF 履歷
├── credentials.json.example         # 🛡️ 資安範本：提供給他人的 Google OAuth 憑證填寫範本
└── README.md                        # 📝 本檔案：專案軟體架構與部署說明書

```

> ⚠️ **資安防護規範 (Data Privacy)**：本專案已嚴格配置 `.gitignore` 機制。真實的連線憑證（`credentials.json`、`token.json`）、雲端暫存檔（`calendar_output.json`、`bookings.json`）皆安全隔離於本地伺服器，切勿推上 GitHub 倉庫。

---

## 🚀 快速開始與本地部署

### 1️⃣ 環境準備與套件安裝

請打開終端機，一鍵安裝本系統所需之所有現代化資料科學與 API 聯絡套件：
```bash
pip install streamlit pandas plotly pypdf pdfplumber gspread yagmail google-genai google-api-python-client google-auth-oauthlib

```

### 2️⃣ 快速上手三步驟

#### 步驟 1：配置金鑰與範本

* 將專案中的 `credentials.json.example` 複製一份，重新命名為 `credentials.json`，並填入您從 Google Cloud Console 申請的桌面版 OAuth 憑證。
* 打開 `main.py` 與 `streamlit_app.py`，於最上方環境參數區填入您的 Gemini API Key 與 Gmail 應用程式密碼。

#### 步驟 2：獲取主管日曆與啟動大腦

```bash
# 1. 抓取兩位用人主管未來 3 週的忙碌時段
python calendar_picker.py

# 2. 啟動 AI 招募核心（選項 1 解析履歷；選項 2 自動分流寄發面邀或感謝信）
python main.py

```

#### 步驟 3：雙開終端機啟動 HR 雙網頁系統

打開兩個獨立的終端機視窗，分別切換至本目錄執行以下指令：

```bash
# 視窗 A：啟動「應徵者預約系統」
streamlit run streamlit_app.py

# 視窗 B：強制指定 Port 8502 啟動「HR 招募戰情室」
streamlit run dashboard.py --server.port 8502

```

---

## 📊 數據驅動招募演算法邏輯

### 💯 AI 嚴格評分機制（滿分 100 分）

* **技術框架一票否決**：應徵者必須熟練 `Flask / FastAPI / Django` 其中至少一種。若無相關經驗，不論學歷多高，總分最高鎖死於 **60 分** 以下，並觸發「AI評分完畢待發感謝信」緩衝狀態。
* **薪資超標預算防呆**：本職缺月薪上限為 **NT$ 70,000**。若求職者期望薪資超出預算，AI 將在總分直接**重扣 15 分**，並於評分原因中註明。

### 🔄 動態內部追蹤機制 (`action_at`)

為確保 HR 部門之招募服務水準（SLA），系統不單記錄投遞時間（`applied_at`），更在以下三大節點自動連動 `action_at`：

1. **AI 評分完畢** ➔ 寫入初始時間。
2. **主管核准/自動攔截寄信** ➔ 押上最後寄發面邀/感謝信時間。
3. **求職者線上預約完成** ➔ 應徵者點擊確認當下，Streamlit 自動將 `action_at` 更新為最新時間，完成無縫查核追蹤。

---

## 🔐 下拉式選單狀態機（Status Machine）

為了防範髒數據（Garbage In, Garbage Out）破壞戰情室分析，Google Sheets 上的 `status` 欄位強烈建議採用「資料驗證」下拉式選單，系統嚴格依循以下狀態機流轉：

```
[新投遞 PDF] ➔ AI 自動評分 ➔ ⚖️ 分數分流：
               ├── 分數 >= 60 ➔ 【AI評分完畢待主管審核】 ➔ 主管打勾 ➔ TRUE  ➔ 【已發面邀未回覆】➔ 應徵者填寫時間 ➔ 【面試排程已確認】 ➔ HR手動改錄取 ➔ 【已錄取】
               │                                                    └── FALSE ➔ 【已發感謝信】
               └── 分數 < 60  ➔ 【AI評分完畢待發感謝信】 ➔ 靜置滿 48 小時 ➔ 【已發感謝信】

```

*註：若錄取人選放棄或接受其他 Offer，HR 可手動於下拉選單選取 `婉拒offer`。*

---

## 📞 技術支援與常見問題排查

1. **出現 `No access token in response` 錯誤？**
* 原因：Google API 發生跨 Scope 的憑證 Token 暫存污染。
* 解法：本系統已於 2026 優化版中導入 `with_scopes()` 憑證隔離機制。若測試期間仍遇到，請直接在終端機按下 `Ctrl + C` 關閉 Streamlit 並重新啟動，即可清空快取。


2. **想要清空日曆上的大量測試行程？**
* 直接執行 `python calendar_clear.py`，輸入 `yes` 即可一鍵秒殺所有含【面試】字樣的測試資料。



---

**最後更新**：2026-05-25

**版本**：2.0 (AI & Analytics 旗艦升級版)

**作者**：國立臺灣大學校學士《組織行為與資料決策》專案團隊

```

```
