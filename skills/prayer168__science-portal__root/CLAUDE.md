# CLAUDE.md — Science Portal for Claude Code
> 最後更新：2026-05-31

---

## 專案說明

「黑熊老師自然科學數位教材中心」
- 網址：https://prayer168.github.io/science-portal/
- 單一檔案：`index.html`（約 140KB）
- 資料庫：Firebase Firestore（`portal/v1`）
- 部署：GitHub Pages（push main 分支即自動更新）

---

## 開發規則

- 所有修改只動 `index.html`
- 繁體中文介面，Traditional Chinese UI
- 不引入任何外部框架（純 HTML/CSS/Vanilla JS）
- 改完後用 `git add index.html && git commit -m "說明" && git push origin main`

---

## 重要函式位置（在 index.html 裡搜尋）

| 搜尋關鍵字 | 說明 |
|-----------|------|
| `MATERIAL_ICON_MAP` | 教材 icon 強制對照表 |
| `applyIconMap` | 套用 icon 對照（掛在兩個資料載入路徑） |
| `DEFAULT_DATA` | 預設教材清單（Firestore 有資料時不生效） |
| `renderManageTable` | 管理列表渲染（含拖曳排序） |
| `_firestoreDataCallback` | Firestore 資料回傳處理 |
| `buildPage` | 重建前台卡片區 |
| `injectCatStyles` | 動態注入類別顏色 CSS |
| `switchTab` | 切換分類（同步管理列表篩選） |
| `initDragSort` | 拖曳排序初始化 |
| `vcCanvas` | 訪客計數器 Canvas |

---

## 陷阱提醒

```
// ❌ 這樣沒用！Firestore 會蓋掉
DEFAULT_DATA.push({cat:"三年級", name:"新教材", ...})

// ✅ 這樣才有用
MATERIAL_ICON_MAP['新教材名稱'] = '🎯'  // 改 icon
// 新增教材請用後台管理介面
```

---

## 詳細文件

完整架構、踩坑記錄、備份資訊請見 `memory.md`
