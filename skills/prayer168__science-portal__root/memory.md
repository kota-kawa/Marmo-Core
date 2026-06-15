# 🐻 Science Portal — memory.md
> 最後更新：2026-05-31　專案：prayer168/science-portal

---

## 1. 專案基本資訊

| 項目 | 內容 |
|------|------|
| 網站名稱 | 黑熊老師自然科學數位教材中心 |
| 網站網址 | https://prayer168.github.io/science-portal/ |
| GitHub Repo | https://github.com/prayer168/science-portal |
| 使用手冊 | https://prayer168.github.io/science-portal-manual/ |
| 使用手冊 Repo | https://github.com/prayer168/science-portal-manual |
| 部署方式 | GitHub Pages（單一 `index.html`） |
| 管理員帳號 | prayer168@gmail.com |
| 資料庫 | Firebase Firestore（`portal/v1` 單一文件） |

---

## 2. 技術架構

```
index.html（單檔）
├── CSS：CSS 變數 + 動態注入類別顏色（injectCatStyles）
├── HTML：
│   ├── loginOverlay（Google 登入彈窗）
│   ├── header（黑熊 favicon + 標題 + 📋使用手冊 + ⚙️管理教材）
│   ├── page-wrap（grid: 236px 1fr）
│   │   ├── aside.sidebar（左側目錄，order:-1）
│   │   └── div.main-col
│   │       ├── manage-panel（後台管理面板）
│   │       └── main.content-area（教材卡片區）
│   └── footer（版權聲明）
├── <script type="module">：Firebase Auth + Firestore onSnapshot
└── <script>：頁面邏輯（CRUD、拖曳、音效、tab 切換）
```

**技術棧：**
- 純 HTML + CSS + Vanilla JS（無框架）
- Firebase Authentication（Google Sign-In）
- Firebase Firestore
- localStorage 離線快取
- Web Audio API（hover 滑動音效）
- GitHub Contents API 部署

---

## 3. 目前功能清單

### 前台
- 左側目錄（sticky）+ 右側教材卡片列表
- 分類 Tab 切換（三年級、四年級、五年級、六年級、教學應用、休閒動動腦、AI程式設計、教案命題）
- Hover 效果：反白 + 晃動動畫 + 滑動音效（Web Audio API，需先點擊頁面啟動）
- 右上角「📋 使用手冊」按鈕（綠色）
- 右上角「⚙️ 管理教材」按鈕（藍色，需登入）
- 黑熊 favicon（透明背景 PNG，以 data URI 嵌入）
- footer：設計者資訊 + 版權聲明（© 2026）
- RWD：760px / 640px / 480px / 360px 四段斷點

### 後台（管理員登入後）
- 類別管理（上方）：新增自訂類別、重新命名（✏）、刪除（✕）
- 新增教材表單：類別 + 名稱 + 網址
- 管理列表：按類別排序 + 右側目錄點擊同步篩選
- 拖曳排序：⠿ 把手 mousedown/mousemove/mouseup，同類別內可拖曳
- 批次操作：勾選多筆 → 刪除 / 移動類別
- 重新命名（inline 編輯）
- 移動類別（下拉選單）
- 刪除（確認後執行）
- 匯出資料（JSON 備份，複製到剪貼簿）
- 打包匯出（Markdown / HTML / PDF / Word，管理員專屬，預設隱藏）
- Firestore 同步狀態指示（☁️ 已同步 / ⏳ 儲存中 / ⚠️ 失敗）

---

## 4. 資料模型

```json
// Firestore: portal/v1
{
  "materials": [
    { "cat": "三年級", "name": "打雷示範動畫", "url": "https://...", "icon": "⚡" }
  ],
  "customCats": [
    { "key": "AI程式設計", "emoji": "🤖", "desc": "AI程式設計", "color": "#e17055", "custom": true },
    { "key": "教案命題", "emoji": "📝", "desc": "教案命題", "color": "#e17055", "custom": true }
  ]
}
```

**資料來源優先順序：**
```
Firestore（最優先）> localStorage 快取 > DEFAULT_DATA（備用）
```

---

## 5. MATERIAL_ICON_MAP（強制覆蓋 icon）

每次資料載入後（Firestore 和 localStorage 兩條路徑）都會執行 `applyIconMap()`：

```js
const MATERIAL_ICON_MAP = {
  '加特林射擊場': '🎯', '月相盈虧互動遊戲': '🌙', '月相變化': '🌙',
  '傅科擺': '🌍', '深海水母': '🌊', 'Q版俄羅斯方塊': '🧩',
  'QR Code 生成器': '🔳', '雨量筒水位模擬1': '🌧️', '雨量筒水位模擬2': '🌧️',
  '雨量筒水位模擬3': '🌧️', '虹吸現象大解密': '💧', '植物蒸散作用': '🌫️',
  '植物有哪些妙招': '🪤', '食蟲植物照顧手冊': '🪤', '台灣外來種植物翻牌': '🌿',
  '台灣外來種動物翻牌': '🐾', '溫度與物質變化': '⚗️', '溫度改變對物質體積的影響': '📏',
  '自然知識大冒險': '🗺️', '巨石陣': '🪨', '開心農場': '🌾',
  '教室互動儀表板': '📊', '智慧錄音': '🎙️', '黑熊老師的使用說明書': '📖',
  '熊學堂': '🏫', '教師用語播放站': '🔊', '網站使用手冊': '📋',
  '用 Claude Code Desktop 打造數位互動教材': '🖥️',
  '使用 Claude Code 編寫數位互動教材': '⌨️',
};
function applyIconMap(arr) {
  arr.forEach(d => { if (MATERIAL_ICON_MAP[d.name]) d.icon = MATERIAL_ICON_MAP[d.name]; });
  return arr;
}
```

---

## 6. ⚠️ 重要陷阱（踩過的坑）

### 坑 1：改 DEFAULT_DATA 沒有用
**問題**：修改程式碼裡的 icon、名稱，前台完全看不到變化。
**原因**：Firestore 資料會蓋過 DEFAULT_DATA。
**解法**：新增到 `MATERIAL_ICON_MAP`，並確保 `applyIconMap` 同時掛在 `loadDataLocal()` 和 `_firestoreDataCallback()` 兩個路徑。
**順序**：`applyIconMap` 函式必須在 `loadDataLocal()` 呼叫之前定義。

### 坑 2：教材名稱要完全一致
**問題**：「月相變化」和「月相盈虧互動遊戲」是兩筆不同教材，ICON_MAP 只對其中一個。
**解法**：ICON_MAP 的 key 必須與 Firestore 裡的 `name` 欄位完全相同（包含全形/半形、空格）。

### 坑 3：打包匯出區塊顯示控制
預設 `display:none`，管理員登入/登出時切換：
```js
document.getElementById('export-pack-box').style.display = isAdmin ? 'block' : 'none';
```

### 坑 4：類別重新命名要同步更新教材的 cat 欄位
```js
DATA.forEach(d => { if (d.cat === oldKey) d.cat = newName; });
```

### 坑 5：拖曳排序的 index 計算
```js
const item = DATA[srcDataIdx];
DATA.splice(srcDataIdx, 1);
const adjustedTgt = tgtDataIdx > srcDataIdx ? tgtDataIdx - 1 : tgtDataIdx;
DATA.splice(adjustedTgt, 0, item);
```
splice 後目標 index 若在來源後面要減 1。

### 坑 6：音效需要先有用戶互動
瀏覽器安全規定：AudioContext 必須在用戶點擊後才能初始化。
```js
document.addEventListener('click', () => getCtx(), { once: false });
```

### 坑 7：favicon 用 data URI 嵌入
直接 `href="favicon.png"` 在某些情況會載入失敗，改成 base64 data URI 嵌入 `<link>` 標籤更穩定。

### 坑 8：GitHub Contents API 檔案大小限制
超過約 100KB 需要改用 git push 或分批處理。Token 每次工作階段都需要重新提供。

### 坑 9：sidebar 左右位置
HTML 結構順序：`main-col` 在前，`sidebar` 在後。
要讓目錄顯示在左邊：`grid: 236px 1fr` + `sidebar { order: -1 }`

---

## 7. GitHub 部署流程

因環境無法使用 git CLI，改用 **GitHub Contents API**：

```python
import json, urllib.request, base64

# 1. 取得目前 SHA
sha = json.load(urllib.request.urlopen(
    urllib.request.Request(
        f"https://api.github.com/repos/{user}/{repo}/contents/{path}",
        headers={"Authorization": f"token {token}"}
    )
))['sha']

# 2. 上傳
with open(file, 'rb') as f:
    encoded = base64.b64encode(f.read()).decode()

data = json.dumps({"message": "commit msg", "content": encoded, "sha": sha}).encode()
req = urllib.request.Request(url, data=data, method='PUT')
req.add_header('Authorization', f'token {token}')
req.add_header('Content-Type', 'application/json')
urllib.request.urlopen(req)
```

---

## 8. 教材備份

- 最新備份日期：**2026-05-23**
- 教材總數：**62 筆**（含後來新增的）
- 備份方式：後台「📋 匯出資料」→ 複製 JSON → 貼給 Claude 保存
- 備份檔名：`science_portal_backup_20260523.json`

**類別與數量（2026-05-31）：**

| 類別 | 數量 |
|------|------|
| 三年級 | 9 |
| 四年級 | 16 |
| 五年級 | 7 |
| 六年級 | 5 |
| 教學應用 | 10 |
| 休閒（動動腦） | 19 |
| AI程式設計 | 11 |
| 教案命題 | 1 |

---

## 9. 相關 Repo 一覽

| Repo | 用途 | 網址 |
|------|------|------|
| `science-portal` | 教材中心主站 | https://prayer168.github.io/science-portal/ |
| `science-portal-manual` | 網站使用手冊 | https://prayer168.github.io/science-portal-manual/ |
| `teacher-chen-manual` | 黑熊老師個人使用說明書（簡報） | https://prayer168.github.io/teacher-chen-manual/ |
| `response-web-design-guide` | RWD 技術指南 | https://prayer168.github.io/response-web-design-guide/ |
| `web_site_skill_guide` | AI Agent 同步指南 | — |

---

## 10. 待辦 / 未來方向

- [ ] 確認拖曳排序在 Firestore 實際存檔後順序是否正確
- [ ] 音效在行動裝置的觸控支援
- [ ] 使用手冊同步更新最新功能（拖曳排序、左側目錄）
- [ ] 考慮將 DEFAULT_DATA 完全廢棄，改以 Firestore 為唯一資料來源
