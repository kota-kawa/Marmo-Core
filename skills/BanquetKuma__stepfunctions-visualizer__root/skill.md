# stepfunctions-visualizer

AWS Step Functions定義（JSON）を視覚化するスキル

## 使い方

```
/stepfunctions-visualizer <path-to-stepfunctions.json> [format]
```

## パラメータ

- `<path-to-stepfunctions.json>`: Step Functions定義JSONファイルのパス（必須）
- `[format]`: 出力形式（省略可、デフォルト: `all`）
  - `mermaid`: Mermaidフローチャート形式
  - `html`: HTML + vis.js インタラクティブ可視化
  - `text`: テキストツリー形式
  - `all`: すべての形式で出力

## 出力ファイル

プロジェクトルートの `images/` ディレクトリに以下のファイルが生成されます：

- `images/{basename}.md`: Mermaidフローチャート（Markdown Preview Mermaid Support拡張機能で表示可能）
- `images/{basename}.html`: HTML可視化（ブラウザで開く）
- `images/{basename}-tree.txt`: テキストツリー

※ `images` フォルダが存在しない場合は自動的に作成されます。

## 機能

- ステートタイプ別の色分け
  - Task: 青
  - Choice: オレンジ
  - Pass/Succeed: 緑
  - Wait: オレンジ
  - Fail: 赤
- Next/Choice/Catch遷移の可視化
- エラーハンドリング（Catch）は点線で表示
- 縦方向レイアウト（Top to Down）
- 統計情報の表示

## 例

```
/stepfunctions-visualizer /path/to/state-machine.json
/stepfunctions-visualizer /path/to/state-machine.json mermaid
/stepfunctions-visualizer /path/to/state-machine.json html
```

## 作成者

BanquetKuma
