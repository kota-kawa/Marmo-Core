"""Japanese translations for Marmo's human-readable CLI messages."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from typing import Any


_JAPANESE = {
    "show this help message and exit": "このヘルプを表示して終了する",
    "Marmo-Core v1 unified resource CLI": "Marmo-Core v1 の統合リソース CLI",
    "validate local resource definition files": "ローカルのリソース定義ファイルを検証する",
    "emit machine-readable JSON": "機械処理用の JSON を出力する",
    "list resources from local definition files": "ローカル定義ファイルのリソースを一覧表示する",
    "search across Memory, Skill, Tool, and Agent resources": "Memory、Skill、Tool、Agent のリソースを検索する",
    "natural-language task description": "タスクを自然言語で記述する",
    "required keyword filter; repeatable": "必須キーワードで絞り込む。複数回指定可",
    "permission granted to the search context; repeatable": "検索時に付与する権限。複数回指定可",
    "drop resources whose permissions are not fully granted": "必要な権限がすべて付与されていないリソースを除外する",
    "maximum number of search results to display": "表示する検索結果の最大件数",
    "limit displayed results per kind; repeatable": "リソース種別ごとの表示上限。複数回指定可",
    "limit selected set per kind; repeatable": "選択する集合でのリソース種別ごとの上限。複数回指定可",
    "drop results below this score": "このスコアを下回る結果を除外する",
    "do not print rule-based selected set": "ルールベースで選択した集合を表示しない",
    "inspect one resource definition including v1 extras": "v1 の追加項目を含めてリソース定義を 1 件表示する",
    "resource id or id@version": "リソース ID または id@version",
    "version to inspect when resource id is ambiguous": "ID だけでリソースを特定できないときに表示するバージョン",
    "evaluate a resource against the Policy Gateway": "Policy Gateway でリソースを評価する",
    "version to check when resource id is ambiguous": "ID だけでリソースを特定できないときに評価するバージョン",
    "permission granted to the current context; repeatable": "現在のコンテキストに付与する権限。複数回指定可",
    "deny resources whose cost_estimate exceeds this value": "cost_estimate がこの値を超えるリソースを拒否する",
    "allowed trust level; repeatable": "許可する信頼レベル。複数回指定可",
    "allowed side effect; repeatable": "許可する副作用。複数回指定可",
    "side effect that requires human approval; repeatable": "人の承認を必要とする副作用。複数回指定可",
    "treat escalation-class risks as already approved": "人の判断が必要な操作が承認済みであるものとして扱う",
    "record that no side effects will be executed by this check": "このチェックで副作用を実行しないことを記録する",
    "tool arguments to inspect at the execution gate": "実行ゲートで検査するツール引数",
    "append a hash-chained JSONL audit record to this path": "ハッシュチェーン付き監査レコードを指定先の JSONL に追記する",
    "run a goal through the guarded kernel loop with the mock LLM or a real provider (--llm)": "モック LLM または実モデル（--llm）で、権限を確認しながら目標を実行する",
    "natural-language goal to execute": "実行する目標を自然言語で記述する",
    (
        "model that drives the run: 'mock' replays --tool-args offline (default); 'openai' and "
        "'anthropic' read OPENAI_MODEL/OPENAI_API_KEY or "
        "ANTHROPIC_MODEL/ANTHROPIC_API_KEY/ANTHROPIC_MAX_TOKENS; 'bedrock' reads "
        "BEDROCK_MODEL/BEDROCK_API_KEY/BEDROCK_REGION from the environment or .env"
    ): (
        "実行に使うモデル。既定の mock は --tool-args をオフラインで再生する。openai と anthropic は "
        "OPENAI_MODEL/OPENAI_API_KEY または ANTHROPIC_MODEL/ANTHROPIC_API_KEY/ANTHROPIC_MAX_TOKENS "
        "を、bedrock は BEDROCK_MODEL/BEDROCK_API_KEY/BEDROCK_REGION を環境変数または .env から読み取る"
    ),
    (
        "how resources are matched to the goal: 'lexical' is offline word matching (default); "
        "'hyde' first asks the --llm to restate the goal in the registry's English vocabulary, "
        "which lets goals written in other languages find English-documented resources"
    ): (
        "目標に合うリソースを探す方法。既定の lexical はオフラインで語彙を照合する。hyde は --llm "
        "に目標をレジストリの英語語彙で言い換えさせ、日本語などの目標から英語で記述されたリソースを探せるようにする"
    ),
    "permission granted to the task context; repeatable": "タスクのコンテキストに付与する権限。複数回指定可",
    "validate and record tool calls without invoking any tool handler": "ツールの処理本体を呼び出さずに、ツール呼び出しを検証して記録する",
    (
        "return non-zero when a resource is skipped or a tool named in --tool-args is not evaluated "
        "(--tool-args counts only where it is used, see its help)"
    ): (
        "リソースがスキップされた場合や、--tool-args のツールが評価されなかった場合は非ゼロで終了する"
        "（--tool-args は使われる場合にだけ数える。--tool-args のヘルプを参照）"
    ),
    "bind a tool resource id to an importable callable; repeatable": "ツールのリソース ID を import 可能な呼び出し先に結び付ける。複数回指定可",
    "bind an agent resource id to a synchronous callable; repeatable": "エージェントのリソース ID を同期の呼び出し先に結び付ける。複数回指定可",
    (
        'arguments per tool id, e.g. \'{"tool.files.read-text": {"path": "README.md"}}\'; used by '
        "--llm mock and by --planner rule, ignored otherwise (a real provider chooses its own arguments)"
    ): (
        'ツール ID ごとの引数。例 \'{"tool.files.read-text": {"path": "README.md"}}\'。'
        "--llm mock と --planner rule で使われ、それ以外では無視される（実モデルは引数を自分で決める）"
    ),
    "search candidates considered before set selection": "集合選択の前に考慮する検索候補の件数",
    "tool call budget before the task fails": "タスクを失敗とするまでに許可するツール呼び出しの上限",
    "times the model may be handed a tool-argument error and asked to call again": "ツール引数が不正なとき、モデルに再試行を求める回数",
    "estimated tokens kept from one tool result before it is truncated (0 to keep all)": "ツールの結果 1 件あたりの推定トークン数の上限。超過分は切り詰める（0 で無制限）",
    "maximum synchronous delegation depth": "同期委譲の最大深さ",
    "maximum cumulative estimated Agent cost": "Agent の累積推定コストの上限",
    "maximum estimated tokens for the compiled execution context": "組み立て後の実行コンテキストに許可する推定トークン数の上限",
    "per-tool execution timeout in seconds": "ツール 1 回あたりの実行タイムアウト（秒）",
    "process mode stops importable handlers at the deadline": "process モードでは期限に達すると import 可能な処理を停止する",
    (
        "append this run's hash-chained audit records to a JSONL file; an existing file's chain "
        "is verified and continued, and a broken chain is refused"
    ): (
        "実行のハッシュチェーン付き監査レコードを JSONL に追記する。既存ファイルのチェーンは検証して"
        "続きに追記し、壊れていれば拒否する"
    ),
    "ask for confirmations on this terminal instead of pausing the task": "タスクを一時停止せず、この端末で承認を求める",
    "answer a paused task's confirmation and continue it": "一時停止したタスクの確認に回答して再開する",
    "model that continues the task; use the same choice as the original run": "タスクを続行するモデル。最初の実行と同じ値を選ぶ",
    "retriever used when the resumed task re-selects resources; match the original run": "再開時にリソースを再選択するときの検索器。最初の実行と同じ値を選ぶ",
    "id of the paused task": "一時停止したタスクの ID",
    "approve the pending operation": "確認待ちの操作を承認する",
    "reject it and end the task": "確認待ちの操作を拒否し、タスクを終了する",
    "leave the task paused for later": "タスクを一時停止のままにする",
    'approve with replacement tool arguments, e.g. \'{"path": "safe.txt"}\'': 'ツール引数を差し替えて承認する。例 \'{"path": "safe.txt"}\'',
    (
        "who is answering; required to approve or modify when --approver is set (checked against --approver)"
    ): "回答者。--approver を指定した場合、承認と修正承認には必須（--approver と照合する）",
    "free-text reason recorded in the audit log": "監査ログに残す自由記述の理由",
    "arguments per tool id for --llm mock or --planner rule; ignored otherwise": (
        "--llm mock または --planner rule で使うツール ID ごとの引数。それ以外では無視される"
    ),
    "match the run's timeout mode": "最初の実行と同じタイムアウトモードを使う",
    "JSONL audit file to continue the hash chain in": "ハッシュチェーンの続きを追記する監査用 JSONL ファイル",
    "list tasks held in a state store": "状態ストアに保存されているタスクを一覧表示する",
    (
        "serve the tool resources to an MCP client over stdio: the client searches for tools by goal "
        "and calls them through the policy gates"
    ): (
        "Tool リソースを stdio の MCP サーバーとして公開する。クライアントは目標でツールを検索し、"
        "ポリシーゲートを通して呼び出す"
    ),
    (
        "resource id or id@version whose side effect is approved in advance; the server cannot ask "
        "for approval, so other tools that need it are refused; repeatable"
    ): (
        "副作用を事前に承認するリソース ID または id@version。サーバーは承認を求められないため、"
        "承認が必要なほかのツールは拒否する。複数回指定可"
    ),
    "most tools one search returns (default: the selector's limit)": "1 回の検索で返すツールの最大数（既定は Selector の上限）",
    "only show tasks in this status": "指定した状態のタスクだけを表示する",
    "lock, verify, and inspect a local resource package": "ローカルリソースパッケージをロック・検証・確認する",
    "pin the manifest and resource files by SHA-256": "マニフェストとリソースファイルを SHA-256 で固定する",
    "directory containing marmo-package.json": "marmo-package.json があるディレクトリ",
    "portable local acquisition path to record in the lock (default: .)": "ロックに記録する、移動可能なローカル取得元のパス（既定値 .）",
    "verify compatibility, source metadata, and all pinned hashes": "互換性、取得元のメタデータ、固定済みのハッシュすべてを検証する",
    "show the verified manifest and lock metadata": "検証済みのマニフェストとロックのメタデータを表示する",
    "directory holding durable task state; without it, state lives in memory only": "タスクの状態を永続化するディレクトリ。省略時はメモリだけに保持する",
    "allow this external hostname and its subdomains; repeatable": "このホスト名とサブドメインへの外部接続を許可する。複数回指定可",
    "deny this external hostname and its subdomains; repeatable": "このホスト名とサブドメインへの外部接続を拒否する。複数回指定可",
    "deny tools whose declared isolation is below this level": "宣言された分離レベルがこの値を下回るツールを拒否する",
    "isolation level supplied by this runtime; repeatable (core default: L0-L2)": "この環境で提供できる分離レベル。複数回指定可（既定 L0～L2）",
    "plan the goal up front instead of letting the model choose call by call": "モデルが呼び出しごとに決める方式に代えて、目標の計画を先に作る",
    "independent plan steps to run at the same time": "並列実行する独立した計画ステップの数",
    "plan revisions allowed after a failure": "失敗後に計画を修正できる回数",
    "executions per step before recovery gives up": "回復を打ち切るまでに許可するステップごとの実行回数",
    "initial exponential backoff in seconds between retries": "指数バックオフの初回の待ち時間（秒）",
    "consecutive failures of one resource before it is cut off": "同じリソースを遮断するまでの連続失敗回数",
    "do not run declared compensating tools when a task fails": "タスクが失敗した場合に、宣言済みの補償ツールを実行しない",
    "resource id that always needs a human before it runs; repeatable": "実行に必ず人の確認を要するリソースの ID。複数回指定可",
    "restrict who may approve; repeatable": "承認できる人を制限する。複数回指定可",
    "resource files or directories": "リソースファイルまたはディレクトリ",
    "do not auto-discover resources, skills, examples/resources, or the current directory": "resources、skills、examples/resources、カレントディレクトリを自動検出しない",
    "resource kind filter; repeatable": "リソース種別で絞り込む。複数回指定可",
    "trust level filter; repeatable": "信頼レベルで絞り込む。複数回指定可",
    "side-effect filter; repeatable": "副作用で絞り込む。複数回指定可",
    "required tag filter; repeatable": "必須タグで絞り込む。複数回指定可",
    "enable the built-in HTTP Connector": "組み込み HTTP Connector を有効にする",
    "allow HTTP destinations on private/loopback networks (unsafe unless intentional)": "プライベート・ループバックネットワークへの HTTP 接続を許可する（意図した場合のみ）",
    "enable the File Connector confined to this directory": "指定したディレクトリ内に限定して File Connector を有効にする",
    "root directory for the Shell Connector (requires --connector-shell-command)": "Shell Connector のルートディレクトリ（--connector-shell-command が必要）",
    "allow one executable in the Shell Connector; repeatable": "Shell Connector で実行可能ファイルを 1 つ許可する。複数回指定可",
    "enable the SQLite Connector for one database path": "指定したデータベースのパスに対して SQLite Connector を有効にする",
    "Connector-local attempts for retry-safe read operations": "安全に再試行できる読み取り操作の Connector 内での試行回数",
    "maximum calls per second for each Connector operation": "Connector の操作ごとの 1 秒あたりの呼び出し上限",
    "consecutive transient failures before a Connector circuit opens": "Connector を遮断するまでの一時的なエラーの連続回数",
    "error": "エラー",
    "warning": "警告",
    "invalid JSON: {detail}": "JSON の形式が正しくありません（{detail}）",
    "--arguments must be a JSON object": "--arguments には JSON オブジェクトを指定してください",
    "--modify must be a JSON object of replacement tool arguments": (
        "--modify には差し替えるツール引数を JSON オブジェクトとして指定してください"
    ),
    "--tool-args must be a JSON object mapping tool ids to argument objects": (
        "--tool-args にはツール ID と引数オブジェクトの対応を JSON オブジェクトとして指定してください"
    ),
    "--modify must not be empty; pass replacement tool arguments as a JSON object": (
        "--modify には差し替えるツール引数を JSON オブジェクトとして指定してください（空は指定できません）"
    ),
    "cannot load {target}: {detail}": "{target} を読み込めません（{detail}）",
    (
        "cannot continue the audit log {path}: {detail}; fix or move the file, or choose another --audit-log"
    ): (
        "監査ログ {path} の続きを書けません（{detail}）。ファイルを修正または退避するか、別の --audit-log を指定してください"
    ),
    "cannot write the audit log {path}: {detail}": "監査ログ {path} に書き込めません（{detail}）",
    "{resource_kind} impl must be ID=MODULE:FUNC: {value}": (
        "{resource_kind} の実装は ID=MODULE:FUNC の形式で指定してください（{value}）"
    ),
    "{target} is not a callable": "{target} は呼び出しできません",
    "--connector-http-allow-private requires --connector-http": (
        "--connector-http-allow-private を使うには --connector-http も指定してください"
    ),
    "--connector-shell-root requires at least one --connector-shell-command": (
        "--connector-shell-root を使うには --connector-shell-command を少なくとも 1 つ指定してください"
    ),
    "limit must be KIND=N: {value}": "上限は KIND=N の形式で指定してください（{value}）",
    "invalid kind in limit: {kind}": "上限に指定されたリソース種別が無効です（{kind}）",
    "invalid numeric limit for {kind}: {raw_limit}": "{kind} の上限を整数で指定してください（{raw_limit}）",
    "limit for {kind} must be non-negative": "{kind} の上限には 0 以上の値を指定してください",
    # Validation from the configuration objects constructed by the CLI.
    "goal must be a non-empty string": "--task には空でない目標を指定してください",
    "context_token_budget must be positive or None": "--context-token-budget には正の整数を指定してください",
    "timeout_seconds must be positive": "--timeout には 0 より大きい秒数を指定してください",
    "max_input_repairs must be >= 0": "--max-input-repairs には 0 以上の整数を指定してください",
    "max_tool_output_tokens must be positive or None": "--max-tool-output-tokens には 0 以上の整数を指定してください",
    "max_cost must be non-negative": "--max-cost には 0 以上の値を指定してください",
    "max_depth must be at least 1": "--max-agent-depth には 1 以上の整数を指定してください",
    "max_total_cost must be non-negative or None": "--max-agent-cost には 0 以上の値を指定してください",
    "max_attempts must be at least 1": "試行回数（--max-attempts または --connector-max-attempts）には 1 以上の整数を指定してください",
    "backoff seconds must be non-negative": "--retry-backoff には 0 以上の秒数を指定してください",
    "failure_threshold must be at least 1": "--circuit-threshold には 1 以上の整数を指定してください",
    "rate_limit_per_second must be positive or None": "--connector-rate-limit には正の値を指定してください",
    "circuit_failure_threshold must be at least 1": "--connector-circuit-threshold には 1 以上の整数を指定してください",
    "warning: could not write {path}: {detail}": "警告: {path} に書き込めませんでした（{detail}）",
    "task": "タスク",
    "status": "状態",
    "output": "出力",
    "detail": "詳細",
    "skipped": "スキップ",
    "awaiting confirmation:": "確認待ち:",
    "  answer with: {command}": "  回答するには次のコマンドを実行してください: {command}",
    "  pass --state-dir to keep the pause resumable across processes": (
        "  別プロセスから再開できるようにするには --state-dir を指定してください"
    ),
    "audit": "監査",
    "{count} records, last_hash={last_hash}…": "{count} 件、最終ハッシュ={last_hash}…",
    "empty": "なし",
    "no tasks found": "タスクが見つかりません",
    "(no paths)": "（パスの指定なし）",
    (
        "note: no resource definitions were found under {paths}. Pass a file or directory of "
        "resource JSON, or run from a checkout that has a resources/ or examples/resources/ directory."
    ): (
        "案内: {paths} にリソース定義が見つかりませんでした。リソースの JSON ファイルまたはその"
        "ディレクトリを指定するか、resources/ または examples/resources/ のあるチェックアウトで実行してください。"
    ),
    (
        "note: --retriever hyde rewrites the goal with --llm, and the mock model replies with a "
        "canned script; the rewrite will steer retrieval at random. Pass --llm openai or "
        "--llm anthropic, or use the default --retriever lexical."
    ): (
        "案内: --retriever hyde は --llm で目標を言い換えます。モックモデルは固定応答を返すため、"
        "検索が意図しない方向に進みます。--llm openai または --llm anthropic を指定するか、"
        "既定の --retriever lexical を使ってください。"
    ),
}


def translate(language: str, message: str) -> str:
    return _JAPANESE.get(message, message) if language == "ja" else message


def japanese_parser_error(message: str) -> str:
    """Keep argparse's argument names and values while explaining common parse errors."""

    for prefix, translation in (
        ("the following arguments are required: ", "必須の引数を指定してください: "),
        ("unrecognized arguments: ", "認識できない引数が指定されました: "),
        ("one of the arguments ", "次の引数のうち 1 つを指定してください: "),
    ):
        if message.startswith(prefix):
            detail = message.removeprefix(prefix)
            if prefix == "one of the arguments ":
                detail = detail.removesuffix(" is required")
            return translation + detail

    argument, separator, detail = message.partition(": ")
    if not separator or not argument.startswith("argument "):
        return message
    option = argument.removeprefix("argument ")
    if detail == "expected one argument":
        return f"{option}: 値を 1 つ指定してください"
    if detail.startswith("invalid choice: "):
        choices_message = detail.removeprefix("invalid choice: ")
        value, marker, choices = choices_message.rpartition(" (choose from ")
        if marker and choices.endswith(")"):
            return f"{option}: {value} は指定できません。選択肢: {choices[:-1]}"
        return f"{option}: {choices_message} は指定できません"
    for prefix, translation in (
        ("invalid int value: ", "整数を指定してください: "),
        ("invalid float value: ", "数値を指定してください: "),
        ("not allowed with argument ", "同時に指定できない引数: "),
    ):
        if detail.startswith(prefix):
            return f"{option}: {translation}{detail.removeprefix(prefix)}"
    return message


class CLIInputError(ValueError):
    """An input error with a translatable message and unmodified argument values."""

    def __init__(self, template: str, **fields: str) -> None:
        super().__init__(template.format(**fields))
        self.template = template
        self.fields = fields


class JapaneseHelpFormatter(argparse.HelpFormatter):
    def add_usage(
        self,
        usage: str | None,
        actions: Iterable[argparse.Action],
        groups: Iterable[Any],
        prefix: str | None = None,
    ) -> None:
        super().add_usage(usage, actions, groups, "使い方: " if prefix is None else prefix)

    def start_section(self, heading: str | None) -> None:
        # Python 3.10 used "optional arguments" for the same section.
        headings = {
            "positional arguments": "位置引数",
            "optional arguments": "オプション",
            "options": "オプション",
        }
        super().start_section(headings.get(heading, heading) if heading is not None else None)
