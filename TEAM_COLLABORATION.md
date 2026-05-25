# 團隊協作指南 - 如何一起改代碼

本文檔說明團隊成員如何協作開發，包括：
- 如何推送你的改動
- 如何看別人的改動
- 如何撤銷錯誤的改動

---

## 📌 核心概念（5 秒速懂）

### 什麼會被記錄？

**只有推送到 GitHub 的改動才會被看到和記錄**

```
你在電腦改代碼
    ↓
git add .              ← 標記改動（還看不到）
    ↓
git commit -m "說明"   ← 建立紀錄（還看不到）
    ↓
git push               ← 推送到 GitHub（✅ 現在所有人都看得到）
    ↓
團隊負責人看到改動 → 可以審查、評論、撤銷
```

---

## 👥 團隊成員的工作流程

### 情況 1：你要推送新改動

**步驟：**

```bash
# 1️⃣ 查看你改了什麼
git status

# 輸出：
# modified:   streamlit_app.py
# new file:   utils.py
```

```bash
# 2️⃣ 添加改動到暫存區
git add .
# 或只添加特定檔案
git add streamlit_app.py
```

```bash
# 3️⃣ 建立提交（寫清楚說明你改了什麼）
git commit -m "Fix bug in time slot validation"

# 說明要清楚，例如：
# ✅ "Fix bug in time slot validation"
# ✅ "Add new feature: email notification"
# ❌ "update" （太含糊）
# ❌ "fix bug" （沒說什麼 bug）
```

```bash
# 4️⃣ 推送到 GitHub（現在所有人都看得到）
git push
```

**完成！你的改動現在在 GitHub 上了。**

---

### 情況 2：你要拉取別人的改動

假設組員 Amy 推送了新代碼，你想更新到最新版本：

```bash
# 拉取最新版本
git pull

# 輸出會顯示：
# Fast-forward
#  streamlit_app.py | 50 ++++++++
#  1 file changed, 50 insertions(+)
```

現在你的本地代碼就跟 GitHub 上一樣了！

---

## 🔍 負責人（你）的查看工作

### 如何看到所有改動？

#### 方法 1：在 GitHub 網頁上查看（最簡單）

1. **進入倉庫首頁**
   ```
   https://github.com/ntu-pbc-hr-project/interview-scheduling-system
   ```

2. **點擊 "Code" 標籤**
   ```
   看到所有檔案
   ```

3. **點擊 "6 Commits"（或當時的提交數量）**
   ```
   看到所有改動歷史
   ```

4. **看提交列表**
   ```
   👤 dingdingdongdong1357  Add detailed comments  ⏰ 11 minutes ago
   👤 Amy                   Fix time validation    ⏰ 5 minutes ago
   👤 Bob                   Add new feature        ⏰ just now
   ```

5. **點擊任何一個提交看詳細改動**
   ```
   會看到：
   - 改了哪些檔案
   - 每一行的改動（綠色=新增，紅色=刪除）
   - 誰改的、什麼時候改的
   ```

#### 方法 2：在本地查看

```bash
# 查看最近 5 次提交
git log -5

# 輸出：
# commit 1735349
# Author: dingdingdongdong1357
# Date: 11 minutes ago
#    Add detailed comments
#
# commit 1234567
# Author: Amy
# Date: 5 minutes ago
#    Fix time validation
```

```bash
# 看特定提交改了什麼（很詳細）
git show 1735349

# 輸出：
# diff --git a/streamlit_app.py b/streamlit_app.py
# index abc1234..def5678 100644
# --- a/streamlit_app.py
# +++ b/streamlit_app.py
# @@ -50,3 +50,5 @@
#  # 舊內容
# +# 新增的內容（綠色）
# -# 刪除的內容（紅色）
```

---

## 🚨 出問題了：如何撤銷改動？

### 情況 1：某個改動有 Bug，需要撤銷

假設 Amy 推送的代碼破壞了整個系統，你要撤銷。

**步驟：**

```bash
# 1️⃣ 查看提交歷史找到 Amy 的提交 ID
git log

# 假設 Amy 的提交 ID 是 abc1234
```

```bash
# 2️⃣ 撤銷該提交（推薦做法）
# 這樣會建立新提交，反轉之前的改動
git revert abc1234
```

```bash
# 3️⃣ 推送到 GitHub
git push
```

**現在 GitHub 上會顯示：**
```
提交 1：Amy - Fix time validation          ✏️
提交 2：你 - Revert "Fix time validation"  ↩️

結果：代碼回到提交 1 之前的狀態
```

### 情況 2：只想撤銷某個檔案的改動

假設 Amy 改了 3 個檔案，但只有 1 個有問題：

```bash
# 1️⃣ 撤銷整個提交
git revert abc1234

# 2️⃣ 把好的 2 個檔案改回來（因為 revert 會改回所有檔案）
git checkout HEAD~1 -- file1.py file2.py

# 3️⃣ 提交
git commit -m "Revert only file3.py, keep file1.py and file2.py changes"

# 4️⃣ 推送
git push
```

### 情況 3：想看改動前後的差異

```bash
# 比較兩個版本的差異
git diff abc1234 def5678

# 或比較特定檔案
git diff abc1234 def5678 -- streamlit_app.py
```

---

## 📋 實際例子：3 人協作情景

### 時間線

```
【週一】
10:00 - 你推送 README.md 改動
       提交 ID: 001

【週二】
14:00 - Amy 推送 streamlit_app.py 改動
       提交 ID: 002

16:00 - 你在 GitHub 上看到 Amy 的改動
       點擊提交 002 查看詳細內容
       發現有問題 → 寫評論

17:00 - Amy 收到評論，在本地修改
       git add streamlit_app.py
       git commit -m "Fix bug from review"
       提交 ID: 003
       git push

【週三】
09:00 - Bob 拉取最新版本
       git pull
       現在 Bob 本地有最新的 001 + 002 + 003

10:00 - Bob 推送他的改動
       提交 ID: 004

15:00 - 你查看提交歷史
       看到完整的時間線：001 → 002 → 003 → 004
       所有人的改動都清清楚楚
```

---

## ✅ 安全檢查清單

推送前，檢查這些：

```
□ 有沒有改到不該改的檔案？ 
  → 執行 git status 確認

□ 提交訊息清楚嗎？
  → 不要寫「update」，要寫「Fix bug in time validation」

□ 有沒有推送敏感檔案？（密碼、API 金鑰）
  → 檢查 .gitignore

□ 本地代碼能運作嗎？
  → 推送前先測試

□ 有沒有最新版本的代碼？
  → 推送前先 git pull
```

---

## 🎯 快速參考：常用命令

### 推送改動
```bash
git status              # 看改動
git add .               # 添加改動
git commit -m "說明"    # 建立提交
git push                # 推送
```

### 拉取別人的改動
```bash
git pull                # 下載最新版本
```

### 查看改動
```bash
git log                 # 看提交歷史
git show <commit_id>    # 看提交詳細內容
```

### 撤銷改動
```bash
git revert <commit_id>  # 反轉提交（推薦）
git push                # 推送反轉
```

---

## 💡 團隊建議

✅ **要做**
- 經常 `git pull` 保持最新
- 寫清楚的提交訊息
- 小改動就立即推送
- 推送前自己測試
- 看到別人的改動就評論回饋

❌ **不要做**
- 改超多東西再一次推送（難以追蹤）
- 寫含糊的提交訊息（「update」「fix」）
- 直接刪除別人的代碼（用 revert）
- 推送未測試的代碼
- 忽視別人的評論

---

## 📞 遇到問題？

| 問題 | 解決方法 |
|------|---------|
| 看不到別人的改動 | 執行 `git pull` |
| 改錯了想撤銷 | 執行 `git revert <commit_id>` |
| 不知道改了什麼 | 執行 `git status` 和 `git diff` |
| 推送失敗 | 執行 `git pull` 再 `git push` |
| 有衝突（同時改同一行） | 編輯衝突檔案，手動選擇保留哪個版本 |

---

## 🎓 進階：用分支避免衝突

如果多人同時改同一個檔案容易衝突，可以用分支：

```bash
# 每個人建立自己的分支
git checkout -b feature/my-feature

# 在自己的分支上工作
git add .
git commit -m "..."
git push -u origin feature/my-feature

# 完成後在 GitHub 上建立 Pull Request（PR）
# 讓負責人審查後再合併到 main
```

這樣可以完全避免衝突！但如果人少（3-4 人），直接在 main 上改也可以。

---

**記住：GitHub 會記錄所有改動，出錯也沒關係，隨時都能撤銷！** 🔒
