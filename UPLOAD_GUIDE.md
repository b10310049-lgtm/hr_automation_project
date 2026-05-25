# GitHub 上傳指南

本文檔說明如何將你的程式碼上傳到 GitHub 倉庫。

---

## 📋 前置需求

1. **Git 已安裝**
   - 檢查：`git --version`
   - 若未安裝，前往 https://git-scm.com/ 下載

2. **GitHub 帳號**
   - 已有帳號即可（不需要建立新的）

3. **倉庫存取權限**
   - 被加入組織 `ntu-pbc-hr-project`
   - 對倉庫 `interview-scheduling-system` 有推送權限

---

## 🚀 快速上傳（適合第一次）

假設你已經修改了某些檔案，現在要上傳。

### 步驟 1：進入專案目錄
```bash
cd d:\200學業\通識課\商管程式設計\期末專案
```

### 步驟 2：初始化本地 Git（只需做一次）
```bash
git init
git config user.name "你的名字"
git config user.email "你的郵箱@gmail.com"
```

### 步驟 3：添加遠端倉庫（只需做一次）
```bash
git remote add origin https://github.com/ntu-pbc-hr-project/interview-scheduling-system.git
```

### 步驟 4：查看有哪些檔案改動
```bash
git status
```

輸出範例：
```
On branch main

Changes not staged for commit:
  modified:   streamlit_app.py
  modified:   README.md
  
Untracked files:
  new_file.py
```

### 步驟 5：添加要上傳的檔案到暫存區
```bash
# 方法 A：添加所有改動
git add .

# 方法 B：只添加特定檔案
git add streamlit_app.py README.md

# 方法 C：互動式選擇（進階）
git add -i
```

### 步驟 6：查看暫存區的檔案
```bash
git status
```

應該看到這樣的輸出：
```
Changes to be committed:
  modified:   streamlit_app.py
  modified:   README.md
  new file:   new_file.py
```

### 步驟 7：建立提交（Commit）
提交時需要寫一條簡短的說明訊息，說明這次改動做了什麼。

```bash
# 簡單說法
git commit -m "Fix bug in streamlit_app.py"

# 詳細說法（會開啟編輯器）
git commit
```

**提交訊息範例：**
```
Add user input validation to streamlit_app.py

- Validate date format before processing
- Add error message for invalid inputs
- Improve user experience with helpful tips
```

### 步驟 8：推送到 GitHub
```bash
git push -u origin main
```

輸出應該像這樣：
```
Enumerating objects: 5, done.
Counting objects: 100% (5/5), done.
Delta compression using up to 4 threads
Compressing objects: 100% (3/3), done.
Writing objects: 100% (3/3), 350 bytes | 175.00 KiB/s, done.
Total 3 (delta 1), reused 0 (delta 0), reused pack (delta 0)
remote: Resolving deltas: 100% (1/1), succeeded
To https://github.com/ntu-pbc-hr-project/interview-scheduling-system.git
   6d18b73..1735349  main -> main
branch 'main' is set up to track 'origin/main'.
```

**成功！** 檔案已上傳到 GitHub ✅

---

## 🔄 之後每次上傳（常用流程）

第一次初始化後，之後每次上傳只需要：

```bash
# 1. 查看改動
git status

# 2. 添加檔案
git add .

# 3. 提交
git commit -m "簡短說明你做了什麼"

# 4. 推送
git push
```

**超快速版本（3 行）：**
```bash
git add .
git commit -m "Fix authentication bug"
git push
```

---

## 🔍 查看 GitHub 上的檔案

1. 前往 https://github.com/ntu-pbc-hr-project/interview-scheduling-system
2. 點擊 **"Code"** 標籤
3. 你會看到整個目錄結構
4. 點擊檔案名稱可以查看內容

### 查看提交歷史
點擊上方的 **提交數量**（例如「5 commits」）可以看到所有提交記錄。

---

## 📊 常用 Git 命令速查表

| 命令 | 說明 |
|------|------|
| `git status` | 查看當前狀態（改動、暫存檔案等） |
| `git add .` | 添加所有改動到暫存區 |
| `git add <檔案>` | 添加特定檔案到暫存區 |
| `git commit -m "說明"` | 建立提交並寫入說明 |
| `git push` | 推送到 GitHub |
| `git pull` | 從 GitHub 下載最新版本 |
| `git log` | 查看提交歷史 |
| `git diff` | 查看檔案的詳細改動 |
| `git reset HEAD <檔案>` | 取消暫存某個檔案 |
| `git checkout <檔案>` | 放棄對檔案的改動（危險！） |

---

## ⚠️ 常見問題

### Q1：出現 "fatal: not a git repository"
**A：** 你可能在錯誤的目錄。確保你在倉庫根目錄（有 `.git` 資料夾的地方）

```bash
# 檢查是否在正確位置
ls -la | grep ".git"

# 或進入正確目錄
cd d:\200學業\通識課\商管程式設計\期末專案
```

### Q2：出現 "Please tell me who you are"
**A：** 需要設定 git 使用者名稱和郵箱

```bash
git config user.name "你的名字"
git config user.email "你的郵箱@example.com"
```

### Q3：出現 "Permission denied (publickey)"
**A：** GitHub 認證失敗。解決方法：

**方法 1：使用 HTTPS（較簡單）**
```bash
git remote set-url origin https://github.com/ntu-pbc-hr-project/interview-scheduling-system.git
git push
# 會要求輸入 GitHub 使用者名稱和密碼（或個人存取 token）
```

**方法 2：設定 SSH 金鑰（進階）**
- 前往 GitHub Settings → SSH Keys
- 建立新 SSH 金鑰
- 將公鑰添加到 GitHub
- 詳見：https://docs.github.com/en/authentication/connecting-to-github-with-ssh

### Q4：不小心 `git add` 了不想上傳的檔案
**A：** 取消暫存

```bash
# 取消暫存某個檔案
git reset HEAD <檔案名稱>

# 取消暫存所有檔案
git reset HEAD
```

### Q5：提交錯誤訊息，想修改
**A：** 修改最後一次提交（只限尚未推送的）

```bash
# 修改提交訊息
git commit --amend -m "新的提交訊息"

# 修改提交內容（添加遺漏的檔案等）
git add <遺漏的檔案>
git commit --amend --no-edit
```

### Q6：推送失敗，說 "Updates were rejected"
**A：** 別人推送了新版本。先拉取再推送

```bash
# 下載最新版本
git pull

# 如果有衝突，手動編輯衝突檔案後再提交
git add .
git commit -m "Merge latest changes"
git push
```

---

## 📝 最佳實踐

### ✅ DO（應該做）
- 提交前執行 `git status` 確認改動
- 寫清楚的提交訊息，說明改了什麼
- 頻繁提交（小改動就提交一次）
- 在推送前拉取最新版本
- 為重大改動建立新分支

### ❌ DON'T（不應該做）
- 提交大量不相關的改動在一個提交
- 寫含糊的提交訊息（如「update」、「fix bug」）
- 提交敏感信息（密碼、API 金鑰、credentials.json）
- 直接修改 main 分支的重大功能（應先建立分支）
- 推送未測試的代碼

---

## 🎓 進階：建立新分支

如果多人同時開發，建議為每個功能建立獨立的分支，避免衝突。

```bash
# 建立新分支
git branch feature/new-feature

# 切換到新分支
git checkout feature/new-feature

# 或一步完成
git checkout -b feature/new-feature

# 在新分支上工作...
git add .
git commit -m "Add new feature"
git push -u origin feature/new-feature

# 完成後可在 GitHub 上建立 Pull Request（PR）請求 merge
```

---

## 📚 參考資源

- **Git 官方文檔**：https://git-scm.com/doc
- **GitHub 說明**：https://docs.github.com/
- **互動式 Git 教學**：https://learngitbranching.js.org/
- **Git 速查表**：https://github.github.com/training-kit/downloads/github-git-cheat-sheet.pdf

---

**有問題嗎？** 聯絡專案主維護者或查看 GitHub Discussions！
