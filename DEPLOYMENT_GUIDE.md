# Streamlit Cloud 部署指南

本文檔說明如何將應用部署到 Streamlit Cloud，並詳細解釋效果和限制。

---

## 📌 快速摘要

| 項目 | 本地運行 | Streamlit Cloud |
|------|---------|-----------------|
| 成本 | 免費 | 免費 |
| 網址 | 無（localhost:8501） | ✅ 有公開網址 |
| Google Calendar 同步 | ✅ 完全可用 | ⚠️ 需配置 Secrets |
| 啟動速度 | 快 | 較慢（15-30秒） |
| 代碼更新 | 手動重啟 | 自動重新部署 |

---

## 🚀 部署步驟（5 分鐘）

### 步驟 1：準備 GitHub 倉庫

確保你的代碼已推送到 GitHub：

```bash
# 檢查倉庫狀態
git status

# 如果有改動，推送
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push
```

**必須有的檔案：**
- ✅ `streamlit_app.py`
- ✅ `requirements.txt`
- ✅ `calendar_sync.py`
- ✅ `calendar_output.json`

**不應有的敏感檔案：**
- ❌ `credentials.json`
- ❌ `token.json`
- （被 `.gitignore` 自動排除）

### 步驟 2：前往 Streamlit Cloud

1. **開啟瀏覽器**
   ```
   https://share.streamlit.io/
   ```

2. **用 GitHub 帳號登入**
   - 點 "Sign up"
   - 選 "Continue with GitHub"
   - 授權 Streamlit

### 步驟 3：建立應用

1. **點右上角**
   ```
   "Create app" 按鈕
   ```

2. **選擇部署方式**
   ```
   ✅ Deploy a public app from GitHub
   ```

3. **填入專案信息**
   ```
   Repository: ntu-pbc-hr-project/interview-scheduling-system
   Branch: main
   Main file path: streamlit_app.py
   ```

4. **點 "Deploy!"**
   ```
   等待 3-5 分鐘...
   ```

### 步驟 4：獲得網址

部署完成後，你會看到：

```
✅ Your app is live at:
https://interview-scheduling-system.streamlit.app
```

**就這樣！應用已上線！**

---

## 📊 效果說明

### ✅ 你能做什麼

**在線上版本中，用戶可以：**

1. **查看可用時段** ✅
   - 看到所有主管的忙碌時間
   - 看到計算出的可用時段
   - 按日期瀏覽時段

2. **選擇時段** ✅
   - 點擊時段方塊
   - 看到時段被高亮選中
   - 反衝突檢測正常運作

3. **界面交互** ✅
   - 完整的 Streamlit UI
   - 所有前端功能正常

### ❌ 你不能做什麼

**以下功能在線上版本受限：**

| 功能 | 本地版 | 線上版 | 原因 |
|------|--------|--------|------|
| 建立 Google Calendar 邀請 | ✅ | ❌ | 缺 Google 凭証 |
| 通知主管 | ✅ | ❌ | 缺 Google 凭証 |
| 同步日曆 | ✅ | ❌ | 缺 Google 凭証 |
| 查看邀請確認 | ✅ | ❌ | 缺 Google 凿証 |

**按「確認預約」時會顯示：**
```
❌ 同步失敗
```

---

## ⚠️ 重要限制

### 1️⃣ 敏感信息安全

**為什麼不上傳 Google 凯證？**

```
credentials.json = 公司的 Google 帳號密鑰
↓
如果上傳到 GitHub → 任何人都能盜用
↓
危險！
```

**最佳實踐：**
```
敏感信息 ❌ 上傳到 GitHub
敏感信息 ✅ 存放在部署環境的 Secrets
```

### 2️⃣ Streamlit 部署的侷限

| 限制 | 詳情 |
|------|------|
| 無持久化存儲 | 應用重啟後，session 資料遺失 |
| 無後端數據庫 | 預約記錄只存在 `bookings.json`（應用內存中） |
| 冷啟動慢 | 第一次訪問需要 15-30 秒啟動 |
| 免費額度有限 | 流量過高會被限制 |

### 3️⃣ Google Calendar 集成限制

線上版本**無法**：
- 讀取實時日曆（使用固定的 `calendar_output.json`）
- 寫入日曆邀請（缺 Google 凭証）
- 自動更新忙碌時段

---

## 🔧 完整功能：本地部署

如果要使用 **所有功能**，必須在本地運行：

```bash
# 1. Clone 倉庫
git clone https://github.com/ntu-pbc-hr-project/interview-scheduling-system.git
cd interview-scheduling-system

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 配置 Google OAuth
# 從 Google Cloud Console 下載 credentials.json
# 放在專案目錄

# 4. 生成日曆數據
python Calendar_FreeTime_Picker.py

# 5. 執行應用
streamlit run streamlit_app.py
```

**本地版本功能：**
- ✅ 查看時段
- ✅ 確認預約
- ✅ 建立 Google Calendar 邀請
- ✅ 通知主管
- ✅ 完整的 Google Calendar 同步

---

## 📋 何時用哪個版本

### 用線上版本（Streamlit Cloud）
- ✅ 演示項目給教授/客戶看
- ✅ 展示界面和邏輯流程
- ✅ 分享代碼給團隊審查

### 用本地版本
- ✅ 實際開發使用
- ✅ 完整功能測試
- ✅ 生產環境部署

---

## 🔐 在 Streamlit Cloud 上啟用完整功能（進階）

如果想在線上版本也有 Google Calendar 功能，需要配置 Secrets：

### 步驟 1：進入應用設定

1. 前往 https://share.streamlit.io/
2. 找到你的應用
3. 點右上角 **⋮ → Settings**

### 步驟 2：添加 Google OAuth 凭證

1. 點 **"Secrets"** 標籤

2. 添加你的 Google OAuth 信息：
```
[google_oauth]
client_id = "你的_client_id.apps.googleusercontent.com"
client_secret = "你的_client_secret"
```

3. 點 "Save"

### 步驟 3：修改代碼（使用 Streamlit Secrets）

編輯 `calendar_sync.py`，改為從 Secrets 讀取：

```python
import streamlit as st

# 從 Streamlit Secrets 讀取
secrets = st.secrets["google_oauth"]
CLIENT_ID = secrets["client_id"]
CLIENT_SECRET = secrets["client_secret"]
```

> **注意：** 這個步驟較複雜，需要修改多個文件。建議只在需要時才做。

---

## 📈 各環境的設置對比

```
開發環境（你的電腦）
├─ credentials.json ✅（本地）
├─ token.json ✅（本地，自動生成）
├─ calendar_output.json ✅
└─ 功能：完全正常

生產環境（公司服務器）
├─ credentials.json ✅（服務器安全存放）
├─ token.json ✅（服務器安全存放）
├─ calendar_output.json ✅
└─ 功能：完全正常

演示環境（Streamlit Cloud）
├─ credentials.json ❌（未配置）
├─ token.json ❌（未配置）
├─ calendar_output.json ✅
└─ 功能：部分（查看 + 選擇，無日曆同步）
```

---

## ✨ 總結

| 需求 | 方案 |
|------|------|
| 要快速演示 | → 用線上版本（Streamlit Cloud） |
| 要完整功能 | → 本地運行 |
| 要生產部署 | → 公司服務器 + Google OAuth 配置 |

這樣的設計符合：
- ✅ 安全最佳實踐（敏感信息不上傳）
- ✅ 業界標準（環境隔離）
- ✅ 開發效率（快速原型 + 完整版本）

---

## 📞 常見問題

**Q：為什麼線上版本看不到時段？**
A：確保 `calendar_output.json` 已推送到 GitHub。

**Q：為什麼點確認預約會失敗？**
A：正常的。線上版本沒有 Google 凯證，這是安全設計。

**Q：怎樣才能在線上版本也建立日曆邀請？**
A：配置 Streamlit Cloud Secrets（進階操作）。

**Q：線上版本的數據會保存嗎？**
A：不會。應用重啟後 session 資料遺失。需要數據庫才能持久化。

---

**部署愉快！** 🚀
