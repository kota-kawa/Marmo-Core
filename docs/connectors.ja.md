# 組み込みコネクター

[English](connectors.md)

Marmo-Core には、標準ライブラリを基盤とする HTTP、ファイルシステム、シェル、SQLite のコネクターが含まれています。各操作は通常の Tool リソースとして登録されるため、リソース選択、アクティベーションと実行の Policy ゲート、ToolRuntime のスキーマ／SecretRef 処理、State Store、Recovery、Audit Log を迂回できません。

## Python API

```python
from marmo_core import (
    FileSystemConnector,
    HTTPConnector,
    Kernel,
    MockLLMProvider,
    PolicyContext,
    ResourceRegistry,
    SQLiteConnector,
    ShellConnector,
)

connectors = (
    FileSystemConnector("./workspace"),
    HTTPConnector(allowed_hosts=("api.example.com",)),
    SQLiteConnector("./workspace/app.sqlite3"),
    ShellConnector("./workspace", allowed_commands=("echo",)),
)

kernel = Kernel(
    ResourceRegistry(),
    MockLLMProvider(),
    connectors=connectors,
    policy_context=PolicyContext(
        granted_permissions=(
            "connector.file.read",
            "connector.http.request",
            "connector.sqlite.read",
            "shell.exec",
        ),
        allowed_external_hosts=("api.example.com",),
        minimum_isolation_level="L1",
    ),
)
```

既定では、`write`、`external`、`irreversible` 操作に、対象を限定した人間の承認が必要です。`dry_run=True` でも権限、信頼度、コスト、隔離レベル、安全規則、入力スキーマを検査しますが、コネクターは呼び出しません。

## CLI の例

固定ルート配下のファイルを読み取ります。

```bash
python3 -m marmo_core.cli run \
  --task "read the note text file" \
  --no-default-resources \
  --strict \
  --connector-file-root ./workspace \
  --granted-permission connector.file.read \
  --minimum-isolation-level L2 \
  --tool-args '{"connector.file.read_text":{"path":"note.txt"}}'
```

HTTP リクエストを送信せずに検証します。

```bash
python3 -m marmo_core.cli run \
  --task "request the example API" \
  --no-default-resources \
  --strict \
  --connector-http \
  --granted-permission connector.http.request \
  --allow-external-host api.example.com \
  --minimum-isolation-level L2 \
  --dry-run \
  --tool-args '{"connector.http.request":{"url":"https://api.example.com/status"}}'
```

シェル展開を無効にして、許可リストにある実行ファイルを1つ実行します。

```bash
python3 -m marmo_core.cli run \
  --task "run the echo command" \
  --no-default-resources \
  --strict \
  --connector-shell-root ./workspace \
  --connector-shell-command echo \
  --granted-permission shell.exec \
  --minimum-isolation-level L1 \
  --dry-run \
  --tool-args '{"connector.shell.run":{"command":"echo hello"}}'
```

固定の SQLite データベースを照会します。

```bash
python3 -m marmo_core.cli run \
  --task "query notes from sqlite" \
  --no-default-resources \
  --strict \
  --connector-sqlite ./workspace/app.sqlite3 \
  --granted-permission connector.sqlite.read \
  --minimum-isolation-level L2 \
  --tool-args '{"connector.sqlite.query":{"sql":"SELECT id, body FROM notes LIMIT 10"}}'
```

`--no-default-resources` を指定すると、カレントディレクトリにある無関係な定義によってコネクターの選択が変わるのを防げます。`--strict` を指定すると、リソースがスキップされた場合、または明示的に設定したツールが評価されなかった場合に、CLI はゼロ以外の終了ステータスを返します。別プロセスでタスクを再開する場合も、これらのフラグを再度指定してください。State Store はタスクとレビュー済み操作を永続化しますが、パス、実行ファイルの許可リスト、ネットワークアクセス、認証情報は実行時の設定のままです。

## セキュリティ境界

- HTTP は HTTP/HTTPS のみを許可し、URL 内の認証情報を拒否し、リダイレクトを追跡せず、応答サイズに上限を設けます。明示的に有効化しない限り、プライベート／ループバック／リンクローカルの宛先をブロックします。リクエスト前に Policy のホスト許可／ブロックリストも適用されます。コネクター自体に `allowed_hosts` リストがある場合は L2、パブリック宛先を制限しない場合は L1 を宣言します。
- ファイル操作では、すべてのパスを1つのルート配下に解決し、絶対パス、ルート外へ抜けるパス、シンボリックリンクを拒否し、読み取りと一覧表示に上限を設けます。書き込みにはアトミック置換を使います。親ディレクトリは事前に存在している必要があります。
- シェルは `shell=False` を指定した `subprocess`、解決済み実行ファイルの許可リスト、ルート内に制限した作業ディレクトリ、環境変数キーの許可リスト、標準入力なし、タイムアウト、永続化する出力のサイズ制限を使用します。これは L1 のプロセス隔離であり、コンテナーやファイルシステムのサンドボックスではありません。
- SQLite は1つのデータベースに固定されます。クエリには読み取り専用接続と行数制限を使います。書き込みでは、明示的な許可リストにある動詞で始まるパラメーター化 SQL 文を1つだけ受け付けます。`ATTACH` とトランザクション制御文は拒否されます。
- コネクター内の再試行は、再試行が安全であると宣言された読み取りにのみ適用されます。書き込み、シェルコマンド、HTTP リクエストは、Kernel の試行ごとに1回実行されます。レート制限とサーキットブレーカーはコネクターの操作ごとに追跡されます。

L3 のコンテナー／VM 隔離、ブラウザー自動化、メッセージング用コネクターは、引き続き v3 の任意項目です。
