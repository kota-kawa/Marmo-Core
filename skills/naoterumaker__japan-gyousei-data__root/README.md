# 🇯🇵 japan-gyousei-data

日本の行政オープンデータにアクセスする [OpenClaw](https://github.com/openclaw/openclaw) スキル。

[MCP サーバー（mcp.n-3.ai）](https://prtimes.jp/main/html/rd/p/000000006.000146070.html) を経由して、3つの政府データソースをリアルタイムに検索・取得できます。

## 📊 データソース

| データ | 提供元 | できること |
|--------|--------|-----------|
| 🏠 不動産取引価格 | 国土交通省 | 都道府県・市区町村の実取引価格データ取得 |
| 📋 官公需（入札） | 官公需情報ポータル | 政府・自治体の調達案件をキーワード検索 |
| 📈 e-Stat 政府統計 | 総務省統計局 | 人口・GDP等の政府統計データ検索 |

## 🚀 使い方

### OpenClaw スキルとして

`skills/` ディレクトリに配置するだけ。以下のような発話で自動発火します：

- 「大阪の不動産価格を調べて」
- 「AI関連の入札情報を検索して」
- 「人口の統計データを取得して」

### スクリプト単体で

```bash
# 不動産: 大阪府の市区町村一覧
bash scripts/mcp-call.sh reinfo reinfolib-city-list '{"area":"27"}'

# 不動産: 大阪市都島区の取引価格（2025年Q3）
bash scripts/mcp-call.sh reinfo reinfolib-real-estate-price '{"year":"2025","quarter":"3","area":"27","city":"27102"}'

# 官公需: AI関連の役務入札を検索
bash scripts/mcp-call.sh kkj kkj-search '{"query":"AI 人工知能","category":"3"}'

# e-Stat: 人口統計を検索
bash scripts/mcp-call.sh estat e-stat-get-stats-list '{"searchWord":"人口"}'
```

## 📁 構成

```
japan-gyousei-data/
├── SKILL.md              # スキル定義（OpenClawが読む）
├── scripts/
│   └── mcp-call.sh       # MCPサーバー呼び出しスクリプト
└── references/
    └── tools.md          # 全ツールのパラメータ詳細
```

## ⚡ 必要なもの

- `curl` と `jq`（どちらも一般的なCLIツール）
- インターネット接続（MCPサーバーへのアクセス）
- **APIキー不要** 🎉

## 🔗 関連リンク

- [MCP サーバー（AI HYVE × N-3）](https://n-3.ai)
- [不動産データ デモ](https://n-3.ai/apps/reinfo-agent)
- [官公需データ デモ](https://n-3.ai/apps/kkj-agent)
- [e-Stat データ デモ](https://n-3.ai/apps/e-stat-agent)
- [OpenClaw](https://github.com/openclaw/openclaw)

## 📄 ライセンス

MIT
