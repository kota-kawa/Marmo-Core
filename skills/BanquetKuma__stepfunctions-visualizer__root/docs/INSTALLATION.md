# インストールガイド

このガイドは、Step Functions Visualizerのすべてのインストール方法について説明します。

## 前提条件

- Python 3.7以上
- Mermaidプレビュー用: Markdown Preview Mermaid Support拡張機能を備えたVS Code
- HTML可視化用: モダンなWebブラウザ

## インストール方法

### 方法1: Claude Code Skill（推奨）

#### グローバルインストール

すべてのプロジェクトにインストール:

```bash
# リポジトリをクローンまたはコピー
git clone https://github.com/BanquetKuma/stepfunctions-visualizer.git
cd stepfunctions-visualizer

# Claude Codeのグローバルskillsディレクトリにコピー
mkdir -p ~/.claude/skills
cp -r . ~/.claude/skills/stepfunctions-visualizer
```

#### プロジェクト固有のインストール

特定のプロジェクトにインストール:

```bash
# プロジェクトディレクトリで
mkdir -p .claude/skills
cp -r /path/to/stepfunctions-visualizer .claude/skills/
```

#### Claude Codeでの使用方法

```
/stepfunctions-visualizer path/to/state-machine.json
```

### 方法2: スタンドアロンPythonスクリプト

#### 直接ダウンロード

```bash
# リポジトリをダウンロード
git clone https://github.com/BanquetKuma/stepfunctions-visualizer.git
cd stepfunctions-visualizer

# 直接実行
python3 visualizer.py path/to/state-machine.json
```

#### PATHに追加（オプション）

システム全体でスクリプトを利用可能にする:

```bash
# 実行可能にする
chmod +x visualizer.py

# 最初の行にshebangを追加（存在しない場合）
# #!/usr/bin/env python3

# /usr/local/binにシンボリックリンクを作成
sudo ln -s $(pwd)/visualizer.py /usr/local/bin/sfn-visualizer

# これで任意の場所から実行可能
sfn-visualizer path/to/state-machine.json
```

## VS Code拡張機能のセットアップ

### Markdown Preview Mermaid Support

1. VS Codeを開く
2. 拡張機能に移動（Ctrl+Shift+X / Cmd+Shift+X）
3. "Markdown Preview Mermaid Support"を検索
4. Matt Biernerによる拡張機能をインストール

### 使用方法

1. Mermaid出力を生成:
   ```bash
   python3 visualizer.py state-machine.json mermaid
   ```

2. 生成された`.md`ファイルをVS Codeで開く

3. `Ctrl+Shift+V`（Windows/Linux）または`Cmd+Shift+V`（Mac）を押してプレビューを表示

## 動作確認

### インストールのテスト

最小限のテストファイルを作成:

```json
{
  "Comment": "Test state machine",
  "StartAt": "HelloWorld",
  "States": {
    "HelloWorld": {
      "Type": "Pass",
      "Result": "Hello World!",
      "End": true
    }
  }
}
```

`test.json`として保存して実行:

```bash
python3 visualizer.py test.json
```

期待される出力:
```
Mermaid diagram saved to: images/test.md
HTML visualization saved to: images/test.html
Text tree saved to: images/test-tree.txt
```

## トラブルシューティング

### Pythonバージョンの問題

`SyntaxError`または`ImportError`が発生した場合:

```bash
# Pythonバージョンを確認
python3 --version

# 3.7以上である必要があります
# そうでない場合は、Python 3.7以上をインストール
```

### Permission Denied

権限エラーが発生した場合:

```bash
# スクリプトを実行可能にする
chmod +x visualizer.py

# またはpython3で明示的に実行
python3 visualizer.py state-machine.json
```

### Claude Code Skillが見つからない

`/stepfunctions-visualizer`コマンドが機能しない場合:

1. skillディレクトリを確認:
   ```bash
   ls ~/.claude/skills/stepfunctions-visualizer
   ```

2. `skill.md`が存在することを確認:
   ```bash
   cat ~/.claude/skills/stepfunctions-visualizer/skill.md
   ```

3. Claude Codeを再起動

### imagesディレクトリが作成されない

出力ファイルが見つからない場合:

1. 現在のディレクトリを確認:
   ```bash
   pwd
   ls -la
   ```

2. `.claude/`または`.git/`ディレクトリを探す（プロジェクトルートマーカー）

3. `images/`ディレクトリを確認:
   ```bash
   ls -la images/
   ```

## アンインストール

### Claude Code Skillの削除

```bash
# グローバル
rm -rf ~/.claude/skills/stepfunctions-visualizer

# プロジェクト固有
rm -rf .claude/skills/stepfunctions-visualizer
```

### スタンドアロンインストールの削除

```bash
# リポジトリを削除
rm -rf /path/to/stepfunctions-visualizer

# シンボリックリンクを削除（作成した場合）
sudo rm /usr/local/bin/sfn-visualizer
```

## 次のステップ

- コード構造を理解するには[DEVELOPMENT.md](DEVELOPMENT.md)を読む
- 可視化をカスタマイズするには[CUSTOMIZATION.md](CUSTOMIZATION.md)を確認
- 使用例についてはメインの[README.md](../README.md)を参照
