# AGENTS.md — Science Portal 專案交接文件
> 適用：OpenAI Codex CLI、Gemini CLI、任何 AI Agent
> 最後更新：2026-05-31

---

## 🚀 快速上手

你正在維護「黑熊老師自然科學數位教材中心」，這是一個**單一 HTML 檔案**的教材入口網站。

**最重要的事：**
- 唯一需要修改的檔案是 `index.html`
- 資料存在 **Firebase Firestore**，不在程式碼裡
- 改了 `DEFAULT_DATA` 沒有用，請用 `MATERIAL_ICON_MAP`
- 部署 = 推送 `index.html` 到 GitHub main 分支，GitHub Pages 自動更新

---

## 📁 檔案結構

```
science-portal/
├── index.html        ← 唯一需要改的檔案（140KB+）
├── favicon.png       ← 黑熊圖示（透明背景）
├── memory.md         ← 完整專案記憶（必讀）
├── AGENTS.md         ← 本文件
├── CLAUDE.md         ← Claude Code 專用
├── skill.md          ← 技術技能文件
└── README.md
```

---

## ⚡ 常用工作流程

### 修改網站內容

```bash
# 1. 取得最新版本
git pull origin main

# 2. 修改 index.html
# （使用你的編輯工具）

# 3. 推送
git add index.html
git commit -m "說明修改內容"
git push origin main
# → GitHub Pages 約 1 分鐘後生效
```

### 新增教材 icon 對照

在 `index.html` 找到 `MATERIAL_ICON_MAP`，加入：
```js
'新教材名稱': '🎯',
```
**注意：** 名稱必須與 Firestore 裡的 `name` 欄位完全一致。

### 新增教材到 DEFAULT_DATA

在 `index.html` 找到 `DEFAULT_DATA` 陣列，加入：
```js
{cat:"四年級", name:"教材名稱", url:"https://...", icon:"🌙"},
```
**注意：** DEFAULT_DATA 只在 Firestore 無資料時才生效。日常新增請用後台管理介面。

---

## 🏗️ 技術架構

| 層次 | 說明 |
|------|------|
| 前端 | 純 HTML + CSS + Vanilla JS（無框架） |
| 認證 | Firebase Authentication（Google Sign-In） |
| 資料庫 | Firebase Firestore（`portal/v1` 文件） |
| 部署 | GitHub Pages |
| 快取 | localStorage |

### 資料流
```
Firestore onSnapshot
  → _firestoreDataCallback(materials, customCats)
    → applyIconMap(materials)   ← 強制套用 MATERIAL_ICON_MAP
    → DATA = materials
    → buildPage()
```

---

## ⚠️ 必知陷阱

1. **改 DEFAULT_DATA 沒有用** → 改 `MATERIAL_ICON_MAP` + `applyIconMap`
2. **`applyIconMap` 函式必須在 `loadDataLocal()` 前定義**
3. **教材名稱要與 Firestore 完全一致**（包含空格、全半形）
4. **類別重新命名時必須同步更新所有教材的 `cat` 欄位**
5. **拖曳排序的 index 計算**：`splice` 後目標 index 若在來源後面需 `-1`

---

## 🔑 重要資訊

- **網站網址**：https://prayer168.github.io/science-portal/
- **管理員帳號**：prayer168@gmail.com
- **後台入口**：右上角「管理教材」或 `Ctrl+Alt+M` 或網址加 `#admin`
- **使用手冊**：https://prayer168.github.io/science-portal-manual/

---

## 📋 最新備份

- 備份日期：2026-05-23，共 62 筆教材
- 如需完整教材清單，請登入後台點「📋 匯出資料」

---

> 詳細內容請閱讀 `memory.md`
