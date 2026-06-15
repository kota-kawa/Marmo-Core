---
name: science-portal
description: >
  互動式數位教材中心建置技能。當使用者想要建立一個收錄多個互動教材連結的網站，
  並具備分類管理、Firebase 雲端同步、Google 帳號後台登入等功能時，使用本技能。
  觸發條件：使用者提到「教材網站」、「教材中心」、「學科入口網站」、
  「Firebase 教材管理」、「互動教材清單」或要求建立帶有後台管理的靜態教學網站。
---

# 互動式數位教材中心建置技能

## 目標

產生一個**單一 HTML 檔案**的互動教材入口網站，具備：

- 多類別分頁瀏覽（可自訂類別與顏色）
- 卡片式教材清單，點擊直接開啟教材
- Firebase Google 帳號登入的後台管理介面
- Firestore 雲端同步（跨裝置資料一致）
- 教材的新增、刪除、移動類別、重新命名
- 批次操作（勾選多筆刪除或移動）
- 自訂類別（新增 / 刪除 / 重新命名）
- 資料匯出（複製 JSON 備份）

---

## 技術架構

| 層次 | 技術 |
|------|------|
| 前端框架 | 純 HTML + CSS + Vanilla JS（無框架依賴） |
| 字體 | Google Fonts：Nunito（英文標題）、Noto Sans TC（中文） |
| 認證 | Firebase Authentication（Google Sign-In） |
| 資料庫 | Firebase Firestore（`portal/v1` 單一文件存全部資料） |
| 部署 | GitHub Pages（單一 `index.html`） |
| 快取 | localStorage 作為離線 / 初次載入快取 |

---

## 資料模型

Firestore 文件路徑：`portal/v1`

```json
{
  "materials": [
    { "cat": "三年級", "name": "打雷示範動畫", "url": "https://...", "icon": "⚡" }
  ],
  "customCats": [
    { "key": "自訂類別", "emoji": "🔭", "desc": "說明文字", "color": "#6c5ce7", "custom": true }
  ]
}
```

預設類別（鎖定，不可刪除）：三年級、四年級、五年級、六年級、教學應用、休閒（動動腦）

---

## Firestore 安全規則

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read:  if true;
      allow write: if request.auth != null
                   && request.auth.token.email == "管理員email@gmail.com";
    }
  }
}
```

---

## HTML 架構

```
<head>
  CSS 變數（每個類別的主色、淺色、柔色）
  動態注入 CSS（injectCatStyles）
</head>
<body>
  登入彈窗（loginOverlay）
  <header>  吉祥物 SVG + 標題 + 管理按鈕
  <nav>     分類 Tab 列（tabBar）
  管理面板  類別管理（上）+ 新增表單 + 管理表格（下）
  <main>    各類別卡片區（category-section）
  <footer>

  <script type="module">  Firebase Auth + Firestore 監聽
  <script>                頁面邏輯（CRUD、tab 切換、批次操作）
</body>
```

---

## 核心函式說明

### 資料流

```
Firestore onSnapshot
  └─▶ window._firestoreDataCallback(materials, customCats)
        └─▶ applyIconMap(materials)        ← 強制套用 icon 對照表
        └─▶ DATA = materials
        └─▶ CATS = [...DEFAULT_CATS, ...customCats]
        └─▶ buildPage()
        └─▶ renderManageTable()
```

### 主要函式

| 函式 | 說明 |
|------|------|
| `buildPage()` | 重建 Tab 列與所有卡片區 |
| `injectCatStyles()` | 根據 CATS 陣列動態注入每個類別的顏色 CSS |
| `syncCatSelects()` | 同步所有 `<select>` 的類別選項 |
| `saveData(d)` | 儲存至 localStorage + Firestore |
| `saveExtraCats(cats)` | 儲存自訂類別至 localStorage + Firestore |
| `renderManageTable()` | 渲染管理後台的教材列表 |
| `applyIconMap(arr)` | 對照 MATERIAL_ICON_MAP 強制修正教材 icon |
| `startRename(idx)` | 將名稱欄位切換為可編輯 input |
| `confirmRename(idx)` | 確認改名並儲存 |
| `moveItem(idx, newCat)` | 移動單筆教材至其他類別 |
| `batchMove()` | 批次移動所選教材 |
| `batchDelete()` | 批次刪除所選教材 |
| `startRenameCategory(key)` | 類別標籤切換為重新命名輸入框 |
| `confirmRenameCategory(key)` | 確認類別改名，同步更新所有教材的 cat 欄位 |

---

## 視覺設計規範

- 主色調：紫色漸層 `#667eea → #764ba2`（Header）
- 卡片陰影：`0 4px 24px rgba(0,0,0,0.07)`，hover 加重
- 動畫：`fadeUp`（0.32s）、`popIn`（登入彈窗）、`spin`（載入轉圈）
- 圓角：`18px`（大容器）、`12px`（卡片）
- 字體大小：clamp(22px, 5vw, 34px)（標題 RWD）
- 每個類別有獨立的主色，會自動計算 `lighten`（12% opacity）和 `soften`（22% opacity）背景色

---

## 同步狀態指示

管理面板右上角的 `#syncStatus` 元素會即時反映 Firestore 操作狀態：

| 狀態 | 文字 | 顏色 |
|------|------|------|
| `loading` | ⏳ 連線中… | #a29bfe |
| `synced`  | ☁️ 已同步  | #00b894 |
| `saving`  | ⏳ 儲存中… | #fdcb6e |
| `error`   | ⚠️ 儲存失敗 | #e17055 |
| `offline` | 📴 離線模式 | #b2bec3 |

---

## ⚠️ 重要陷阱與注意事項

### 1. Firestore 優先，DEFAULT_DATA 只是備用

**問題**：修改程式碼裡的 `DEFAULT_DATA`（icon、名稱等），前台完全看不到變化。

**原因**：網站啟動後 Firestore 資料會蓋過 DEFAULT_DATA，localStorage 快取也會優先被讀取。

**解法**：
- 使用全域 `MATERIAL_ICON_MAP` + `applyIconMap()` 函式，在每次資料載入後強制套用
- `applyIconMap` 必須**同時**掛在 `loadDataLocal()` 和 `_firestoreDataCallback()` 兩個路徑上
- 注意：`applyIconMap` 函式必須在 `loadDataLocal()` 被呼叫之前就定義好，否則會報錯

```js
// 正確的定義順序
const MATERIAL_ICON_MAP = { '教材名稱': '🎯', ... };
function applyIconMap(arr) {
  arr.forEach(d => { if (MATERIAL_ICON_MAP[d.name]) d.icon = MATERIAL_ICON_MAP[d.name]; });
  return arr;
}
function loadDataLocal() {
  return applyIconMap(...); // ← 這裡才能呼叫
}
```

### 2. 教材名稱要完全一致才能對應到 ICON_MAP

**問題**：「月相變化」和「月相盈虧互動遊戲」是兩筆不同教材，ICON_MAP 只對其中一個，另一個不會改。

**解法**：ICON_MAP 的 key 必須與 Firestore 裡的 `name` 欄位**完全相同**（包含全形/半形、空格）。

### 3. 更改程式碼 DEFAULT_DATA 不會更新 Firestore

**問題**：在 DEFAULT_DATA 新增或刪除教材，Firestore 不會跟著變。

**解法**：
- 日常新增/編輯教材 → 用**後台管理介面**操作
- 大量更新 → 後台匯出 JSON → 修改後請 Claude 幫忙透過 Firestore API 匯入

### 4. 資料備份流程（每次大改前必做）

1. 登入後台管理員
2. 點「📋 匯出資料（複製）」
3. 將 JSON 貼給 Claude 保存，或自行存檔

最新備份日期：**2026-05-23**，共 62 筆教材。

### 5. 打包匯出區塊的顯示控制

「打包匯出」側欄區塊預設 `display:none`，僅管理員登入後顯示。
控制邏輯掛在 `onAuthStateChanged` 的登入/登出回呼裡：

```js
document.getElementById('export-pack-box').style.display = isAdmin ? 'block' : 'none';
```

### 6. 類別重新命名注意事項

重新命名類別時，必須同步更新所有教材的 `cat` 欄位，否則教材會消失在舊類別下：

```js
DATA.forEach(d => { if (d.cat === oldKey) d.cat = newName; });
```

---

## 部署流程

由於 git 根目錄與專案目錄不同層，使用 GitHub Contents API 部署：

```powershell
# 1. 取得目前遠端 SHA
$sha = gh api repos/USER/REPO/contents/index.html --jq '.sha'

# 2. Base64 編碼（無 BOM）
$bytes = [System.IO.File]::ReadAllBytes("index.html")
$b64   = [System.Convert]::ToBase64String($bytes)

# 3. 組 JSON payload（無 BOM UTF-8）
$json = [PSCustomObject]@{ message="commit message"; content=$b64; sha=$sha } |
        ConvertTo-Json -Compress
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText("payload.json", $json, $utf8NoBom)

# 4. 推送
gh api repos/USER/REPO/contents/index.html --method PUT --input payload.json

# 5. 清理
Remove-Item payload.json
```

---

## 擴充建議

- **拖曳排序**：在 `card-grid` 加入 SortableJS 實現卡片拖曳
- **搜尋**：在 Tab 列上方加入即時搜尋框，過濾 `DATA` 渲染
- **教材預覽**：在卡片加入 `<iframe>` 預覽彈窗
- **多管理員**：Firestore 規則改為讀取 `admins` 集合白名單
- **教材計數徽章**：用 Firestore `increment` 記錄每個教材的點擊次數
