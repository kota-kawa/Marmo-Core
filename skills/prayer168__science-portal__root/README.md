# 🐻 黑熊老師自然科學數位教材中心

> 一個專為自然科課堂設計的互動教材入口網站，收錄三～六年級、教學應用、休閒益智等各類數位教材，一鍵開啟互動體驗。

🔗 **線上網址**：[https://prayer168.github.io/science-portal/](https://prayer168.github.io/science-portal/)

---

## ✨ 功能特色

### 前台（所有人）
- 📚 依年級 / 類別分頁瀏覽教材
- 🃏 卡片式介面，點擊直接開啟互動教材
- 📱 RWD 響應式設計，手機、平板、電腦皆適用
- ⚡ 初次載入後快取至本機，離線可瀏覽

### 後台（管理員）
- 🔐 Firebase Google 帳號登入（限指定管理員）
- ☁️ Firestore 雲端同步，跨裝置資料一致
- ➕ 新增教材（類別、名稱、網址）
- ✏️ 重新命名教材（直接在表格中內嵌編輯）
- 📂 移動教材到其他類別（單筆 / 批次）
- 🗑️ 刪除教材（單筆 / 批次勾選）
- 🗂️ 新增 / 刪除自訂類別
- 📋 匯出教材 JSON 備份

---

## 🖥️ 畫面預覽

```
┌────────────────────────────────────────────┐
│  🐻  黑熊老師自然科學數位教材中心          │  ← 台灣黑熊吉祥物 + 熊掌背景
│  🐾 台灣黑熊 · 守護自然                    │
├────────────────────────────────────────────┤
│  🌱三年級  🌿四年級  🌲五年級  🌏六年級 … │  ← 類別 Tab
├────────────────────────────────────────────┤
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
│  │ ⚡   │ │ 🌧️   │ │ 🌤️   │ │ 🎐   │      │  ← 教材卡片
│  │打雷  │ │雨天  │ │天氣  │ │風向  │      │
│  │示範  │ │動畫  │ │特派員│ │彩帶計│      │
│  └──────┘ └──────┘ └──────┘ └──────┘      │
└────────────────────────────────────────────┘
```

---

## 🛠️ 技術架構

| 項目 | 說明 |
|------|------|
| 語言 | HTML5 / CSS3 / Vanilla JavaScript（無框架） |
| 字體 | Nunito（標題）、Noto Sans TC（中文） |
| 認證 | Firebase Authentication v10（Google Sign-In） |
| 資料庫 | Firebase Firestore v10（即時同步） |
| 快取 | localStorage（離線備援） |
| 部署 | GitHub Pages |
| 檔案數 | 單一 `index.html`（< 50 KB） |

---

## 🚀 快速開始

### 1. 複製專案

```bash
git clone https://github.com/prayer168/science-portal.git
cd science-portal
```

### 2. Firebase 設定

1. 前往 [Firebase Console](https://console.firebase.google.com/)
2. 建立專案 → 啟用 **Authentication**（Google 登入）
3. 啟用 **Firestore Database**
4. 將 `index.html` 中的 `firebaseConfig` 改為您的設定：

```javascript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.firebasestorage.app",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};
```

5. 修改管理員 Email：

```javascript
const ALLOWED_EMAIL = "your-email@gmail.com";
```

### 3. Firestore 安全規則

在 Firebase Console → Firestore → 規則，貼上：

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read:  if true;
      allow write: if request.auth != null
                   && request.auth.token.email == "your-email@gmail.com";
    }
  }
}
```

### 4. 部署至 GitHub Pages

```bash
git add index.html
git commit -m "init: deploy science portal"
git push origin main
```

在 GitHub repo → **Settings → Pages → Source: main branch** → Save

---

## 📁 專案結構

```
science-portal/
├── index.html   # 整個網站（前台 + 後台 + Firebase 整合）
├── README.md    # 本說明文件
└── skill.md     # Claude Code 技能說明（如何重建本網站）
```

---

## 📖 使用說明

### 管理員操作流程

1. 點擊右上角 **⚙️ 管理教材**
2. 未登入時會彈出 Google 登入視窗
3. 登入成功後，管理面板自動展開

#### 新增教材
填入「類別」、「名稱」、「網址」後按 **新增 ＋**，或在名稱欄位按 Enter 跳至網址欄，網址欄按 Enter 直接新增。

#### 重新命名
在管理表格中點擊 **✏️ 改名**，名稱欄位變成輸入框，按 Enter 或 ✓ 確認，Esc 取消。

#### 移動類別
- **單筆**：點擊該列的「📂 移到…」下拉選單選擇目標類別
- **批次**：勾選多筆 → 在批次工具列選擇目標類別 → **📂 移動到此類別**

#### 新增自訂類別
在管理面板最下方「🗂️ 類別管理」輸入圖示（emoji）和名稱，按 **新增類別 ＋**。

---

## 🎨 教材類別與顏色

| 類別 | 圖示 | 主色 |
|------|------|------|
| 三年級 | 🌱 | `#FF6B6B` 珊瑚紅 |
| 四年級 | 🌿 | `#FF9F43` 橘黃 |
| 五年級 | 🌲 | `#1DD1A1` 翠綠 |
| 六年級 | 🌏 | `#54A0FF` 天藍 |
| 教學應用 | 💡 | `#00B894` 青綠 |
| 休閒（動動腦）| 🎮 | `#A29BFE` 薰衣草紫 |

---

## 🐻 關於台灣黑熊

網站吉祥物採用**台灣黑熊**（*Ursus thibetanus formosanus*），又名亞洲黑熊台灣亞種。最具代表性的特徵是胸前的白色月形（V形）胸紋，是台灣珍貴的保育類動物。

> 保育台灣黑熊，從認識自然科學開始 🌿

---

## 📄 授權

本專案供教學使用，教材連結版權屬原作者所有。

---

*由 Prayer 老師（黑熊老師）建置 · Powered by Firebase & GitHub Pages*
