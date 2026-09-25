# Marmo-Core Architecture

内部設計の正本。公開向けの説明は `README.md`、契約の変更手順は
`docs/knowledge/contracts-and-compatibility.md`、判断の経緯は `docs/decisions/`
にある。ここには「今どう動いているか」だけを書く。実装と食い違いを見つけたら、
この文書を直すか実装を直すかを決めて同じ PR で揃える。

対象バージョン: `marmo_core/_version.py` の値（現在 0.6.0）。

## 1. 位置づけ

Marmo-Core は、AI エージェントが使う **リソース**（Memory / Skill / Tool /
Agent の 4 種別）を登録し、ゴールに対して必要なものだけを検索・選択し、ポリシーと
人間確認のゲートを通して実行する Python カーネルである。実行時依存は
`python-dotenv` のみで、HTTP は `urllib`、永続化は JSONL / SQLite の標準ライブラリで
賄う。LLM プロバイダ、埋め込み、cross-encoder は差し替え可能な境界の外にある。

## 2. レイヤー構成

依存は下の層から上の層へ一方向に流れる。`kernel.py` がほぼ全層を束ねる。
モジュールの責務は `marmo_core/<module>.py` の docstring と、対応するテストで確認する。

| 層 | モジュール | 責務 | 依存先（marmo_core 内） |
|---|---|---|---|
| 基盤 | `errors.py` | 例外階層（`MarmoError` の下に `ResourceLoadError`、`PackageError`、`ActivationError`、`ToolInputError`、`ProviderError`→`ProviderHTTPError` など） | なし |
| 基盤 | `environment.py` | `.env` の遅延読み込み（`override=False`、OS 環境変数が優先）と `required_environment` 系ヘルパー | なし |
| 基盤 | `security.py` | 隔離レベル（L0〜L3）、`PromptInjectionInspector`、`label_untrusted_content` | なし |
| 基盤 | `secrets.py` | `{"$secret": ...}` 参照、`SecretResolver`、`redact_credentials`（伏せ字パターンの唯一の置き場） | errors |
| リソースモデル | `models.py` | `ResourceKind`、`ResourceMetadata`、`ResourceDefinition`、`SearchQuery`、`SearchResult`、`SelectionResult` | security |
| レジストリ・ロード | `registry.py` | `ResourceRegistry`（`revision` と `content_revision`） | errors, models |
| レジストリ・ロード | `markdown_skill.py` | `SKILL.md` フロントマター → Skill 定義 | models |
| レジストリ・ロード | `package.py` | `marmo-package.json` / `.lock.json`、SemVer、`verify_local_package` | _version, errors |
| レジストリ・ロード | `loader.py` | ディレクトリ走査（`.json` / `.md`）、`load_registry`、`validate_resource_paths` | errors, markdown_skill, models, package, registry |
| 検索 | `retriever.py` | `Retriever` ABC、BM25F 転置インデックスの `LexicalRetriever`、複合スコア | models, registry |
| 検索 | `semantic.py` | `EmbeddingProvider` ABC、`HashingEmbeddingProvider`、`OpenAICompatibleEmbeddingProvider`、`HybridRetriever` | environment, errors, models, registry, retriever, secrets |
| 検索 | `graph_routing.py` | `CapabilityGraphRetriever`（依存・capability 名前空間で候補を拡張） | models, registry, retriever, semantic |
| 検索 | `hierarchy.py` | `HierarchicalRetriever`、`GroupingStrategy`（namespace / provider / permission / embedding） | models, registry, retriever, semantic |
| 検索 | `rerank.py` | `CrossEncoderProvider` ABC、`CrossEncoderRerankRetriever` | models, registry, retriever |
| 検索 | `llm_routing.py` | `HydeRetriever`、`LLMRerankRetriever`、`LLMSetSelector` | llm, models, registry, retriever, selector |
| 選択 | `selector.py` | `SetSelector` ABC、`SelectionContext`、`RuleBasedSetSelector`（既定）、Greedy / Beam / BranchAndBound の制約付きソルバー | models |
| 選択 | `adaptive.py` | `CaseBasedRouter`、`RoutingCaseStore`（Kernel には組み込まれていない） | errors, models, registry, retriever, selector, semantic |
| 選択 | `evaluator.py` | `ExecutionEvaluator`（監査ログ → `ResourceStats` 書き戻し。Kernel からは呼ばれない） | audit, models, registry |
| ポリシー | `safety.py` | `SafetyInspector`（破壊的コマンド・持ち出し検知）、`redact_sensitive_arguments` | models, secrets |
| ポリシー | `policy.py` | `PolicyContext`、`PolicyGateway.evaluate(gate=activation/execution/output)`、`PolicyRejectedError` | errors, models, safety, security |
| 実行 | `activator.py` | `ResourceActivator`（activation gate → `InjectedMemory` / `LoadedSkill` / `BoundTool` / `BoundAgent`、`python:` 参照の解決） | errors, models, policy |
| 実行 | `tool_runtime.py`、`process_execution.py` | `ToolRuntime.execute`（execution gate、シークレット解決、スキーマ検証、dry-run、タイムアウト）。任意指定の process モードは import 可能なハンドラを子プロセスで実行・停止する | activator, errors, policy, secrets |
| 実行 | `agent_runtime.py` | `AgentRuntime`（Agent を Tool として包む。権限は縮小のみ、深さ・コスト上限） | activator, errors, policy, tool_runtime |
| 実行 | `compiler.py` | `ContextCompiler`（予算と優先度で Memory をトリム、`AgentInterface`） | activator, llm, models, security |
| 実行 | `planner.py` | `Plan` / `PlanStep`、`Planner` ABC、`RuleBasedPlanner`、`LLMPlanner` | errors, llm, models, policy, secrets |
| 実行 | `recovery.py` | `RecoveryManager`、`RetryPolicy`、`CircuitBreaker`、補償 | models |
| 実行 | `kernel.py` | `Kernel`、`TaskResult`。全層の束ね役 | ほぼ全部 |
| プロバイダ | `llm.py` | `LLMProvider` ABC、`ChatMessage`、`ToolCall`、`MockLLMProvider`、`estimate_tokens` | secrets |
| プロバイダ | `providers.py` | `ToolNameCodec`、`AnthropicLLMProvider`、`OpenAICompatibleLLMProvider`（urllib、`transport` 注入可） | environment, errors, llm, semantic |
| 状態・監査・HITL | `state.py` | イベントソーシングの `StateStore` ABC と InMemory / JsonFile / SQLite 実装、`TaskState`、`Checkpoint` | errors, secrets |
| 状態・監査・HITL | `audit.py` | `AuditRecord`、`AuditLog`（SHA-256 ハッシュチェーン）、`mask_sensitive` | secrets |
| 状態・監査・HITL | `hitl.py` | `HitlRequest` / `HitlResponse` / `HitlPolicy`、`HitlBroker` ABC と Pending / Callback / Console / AutoApprove | errors, models |
| コネクタ | `connectors.py` | `Connector` ABC、`ConnectorRuntime`（レート制限・リトライ・サーキット）、HTTP / FileSystem / Shell / SQLite | errors, models, registry |
| コネクタ | `mcp.py` | `MCPStdioClient`、`connect_mcp_server`（既定 trust=community、side_effect=external） | _version, errors, models |
| CLI | `formatting.py`、`cli.py` | 出力整形と argparse による `marmo` コマンド | ほぼ全部 |
| サンプル | `sample_resources/` | `resources/*.json` から `python:` 参照される決定的なハンドラ | なし |

## 3. リクエスト経路

### 3.1 `Kernel.run_goal(goal)`

1. `run_goal` → `submit`（`created` イベント）→ `run` → `_drive`。`_drive` は `pending`
   があれば `hitl.request` を呼び、`_execute` を最大 `max_hitl_rounds` 回繰り返す。
2. `_execute` は `status=running` と trace_id を記録し、人間の承認と付与済み権限を
   `PolicyContext` に合流させる。
3. **検索** `_candidate_pool`: `retriever.search(registry, SearchQuery)` の結果から、
   activation gate で deny されるものを除く（ただし各 kind の首位は残す）。件数が
   足りない kind があれば、kind 限定の追加検索を **1 回だけ** 行う（1 ゴールあたり
   検索は最大 2 回）。
4. **選択** `selector.select(results, context=SelectionContext)` → `audit("retrieve")`。
   `escalate` なら `_pause`（selection ステージの `HitlRequest`）。
5. **Activation gate** `activator.activate` → `PolicyGateway.evaluate(gate="activation")`
   → `audit("policy")`。escalate は `_pause`、deny は skipped に入れて
   `recovery.classify_activation`。
6. **コンテキスト構築** `compiler.compile(...)` → `audit("compile")`。Memory は
   `PromptInjectionInspector` を通し、検知すれば `audit("security")`。
7. **会話フレームの復元** `state.frame` から messages、実行済み呼び出し、修正回数などを
   戻す。`planner` があれば `_execute_plan` に分岐し、Plan の DAG を wave 単位で実行。
8. **LLM 呼び出し** `llm.complete(messages, compiled.tools)` → `audit("llm")`。
   `ProviderError` はタスクを `failed` で終端させる（例外は外に出さない）。
9. **Tool call の解析** プロバイダが `ToolNameCodec.decode` で wire 名を resource id に
   戻す。呼び出しが無ければ `completed`。未知の callable やスキーマ違反は tool
   メッセージでモデルに差し戻す（上限 `max_input_repairs`）。`max_tool_calls` は
   **実行した呼び出し数** を数え、超えれば `failed`。
10. **Tool 実行** `_run_tool_call`: 平文シークレット拒否 → `always_confirm` 判定 →
    `checkpoint("before:<call_id>")` → `tool_runtime.execute`（execution gate、
    シークレット解決、`SafetyInspector`、スキーマ検証、dry-run、タイムアウト）。
    escalate は `_pause`、deny は `denied`。Agent は `agent_runtime.execute` 経由で同じ
    `ToolRuntime` を通る。timeout は副作用の結果が不明なため自動再試行・代替を行わない。
11. **Recovery** 失敗は `recovery.classify_tool_result` → `decide` で retry / fallback /
    escalate / fail（`_abort` と補償）。
12. **書き戻し** `audit("execute")` と `step` イベント。ツール出力は
    `PromptInjectionInspector` → `label_untrusted_content`（`max_tool_output_tokens` で
    切り詰め、閉じタグは必ず残す）→ messages。ラウンドごとに `frame` を保存。
13. **終了** `_finish` が `status` イベントと `audit("task")` を書いて `TaskResult` を返す。
    `_pause` は `paused` イベントと `audit("hitl")` を書き、status=escalated を返す。
14. **実績統計** Kernel は書き戻さない。呼び出し側が `ExecutionEvaluator().ingest_audit(
    kernel.audit_log)` と `.apply(registry)` を呼ぶと `ResourceStats` が更新され、
    `LexicalRetriever` の success 項に反映される。`stats` だけの更新は
    `content_revision` を動かさないので、索引と埋め込みは再構築されない。

### 3.2 `marmo run` / `marmo resume`

- `run`: `_build_kernel(continue_audit=False)` が `load_registry`（既定パスは
  `resources/`、`skills/`、`examples/resources/` の順。`--no-default-resources` で無効）、
  CLI 引数からの `PolicyContext` と `HitlPolicy`、`ConsoleHitlBroker`（`--confirm`）
  または `PendingHitlBroker`、`_build_llm`（mock / openai / anthropic）、
  `_build_retriever`（lexical / hyde）、planner、connectors、
  `JsonFileStateStore(--state-dir)` を組み立て、`kernel.run_goal(--task)` を実行する。
  `_report_task` が `--audit-log` の書き出しと `--strict` の検査を行う。終了コードは
  completed=0、それ以外=1、例外=2。
- `resume`: `_build_kernel(continue_audit=True)` が既存の `--audit-log` を
  `AuditLog.from_jsonl`（チェーン検証あり）で読み、`--approve/--reject/--defer/--modify`
  から `HitlResponse` を作って `kernel.resume(task_id, response)` を呼ぶ。選択が確定したら
  resource identity と内容 fingerprint を state の `snapshot` event に保存し、再開時は
  検索・選択を繰り返さない。Resource 定義またはコンパイル済み context が変わっていれば
  task を失敗で終端する。HITL 前に読み込んだ memory / skill の本文 fingerprint も保存し、
  activation 中に一時停止した後で本文が変わった場合も失敗で終端する。snapshot 導入前の
  activation / execution pause は対象を復元できないため失敗で終端する。LLM ループは保存済み `frame` から復元されるため
  実行済みの呼び出しは二度走らない。一時停止時に表示される resume コマンドは、実行時の
  `--granted-permission` / `--allow-side-effect` を必ず再現する。

## 4. 契約と境界

詳細と変更手順は `docs/knowledge/contracts-and-compatibility.md`。

- **公開 API**: `marmo_core/__init__.py` の `__all__`。`tests/test_compatibility.py` が
  `tests/fixtures/compat/v0.3.0/public_api.txt` の全名前が残っていることを検証する
  （削除のみ検出、追加は許容）。
- **ResourceDefinition**: `metadata`（必須 15 フィールド + 任意の `dependencies`、
  `conflicts_with`、`stats`）と kind ごとの `extras`（tool: `input_schema` /
  `output_schema` / `isolation_level`、agent: `delegation_interface` / `agent_card`、
  memory: `content`、skill: `instructions` / `content`）。フラット形式と
  `{"metadata": ...}` 形式の両方を受け付ける。identity は `id@version`。
- **状態ファイル**: `<state-dir>/<task_id>.jsonl`。各行は
  `{schema_version: 1, task_id, seq, timestamp, kind, payload}`、kind は
  `state.EVENT_KINDS`。seq の単調増加で楽観ロック（`StateConflictError`）。
- **実行 Snapshot**: 選択確定後に `snapshot` event へ選択 identity・スコア・
  fingerprint を追記する。memory / skill は activation で本文を読んだ時点で fingerprint を
  追記する。再開時に同じ選択を復元し、selected Resource・読み込み済み本文・compiled context
  の fingerprint が変わった場合は実行を拒否する。
- **タスク予算**: `Kernel(task_budget=TaskBudget(...))` は通貨とモデル単価を明示し、
  `budget` event に設定・予約・精算を追記する。再開時は同じ設定が必要。rollback でも
  実行済み費用は戻さない。selector には残額を渡し、モデル呼び出しと各 Tool / Agent 試行の
  前に予約する。モデル出力上限は `complete_bounded()` で wire request に渡し、入力上限は
  メッセージと Tool schema を含むシリアライズ済み入力の推定値で確認する。カスタム
  `LLMProvider` は同メソッドを実装して `supports_output_token_limit=True` を宣言する。
  外部サービスを利用する handler の費用は Resource 見積りに含める。
  カスタム Retriever / Selector / Planner を予算付きで使用する場合、その実装が
  `budget_aware=True` を宣言し、内部の有料呼び出しを予算管理する責任を持つ。
- **監査ログ**: `{trace_id, span_id, timestamp, kind, payload（マスク済み）, prev_hash, hash}`。
  hash は `hash` 以外を正規化 JSON にした SHA-256、`prev_hash` は直前レコードの hash。
  `verify()` と `from_jsonl` がチェーンを検証する。
- **ToolNameCodec**: `[^a-zA-Z0-9_-]` を `_` に置換。64 文字超や衝突は先頭 55 文字 +
  `_` + sha1 先頭 8 桁。カーネルと監査ログは常に元の resource id を見る。
- **プロバイダとの wire 契約**: `openai.com` には `max_completion_tokens`、他の
  OpenAI 互換サーバーには `max_tokens`。未対応と返されたら 1 回だけ切り替える。
  エラー本文は `redact_credentials` を通してから例外・ログに出す。
- **CLI 終了コード**: `run` / `resume` は completed=0、denied / failed / escalated=1、
  例外=2。`--strict` は「候補になった Tool / Agent が 1 つもモデルに届かなかった」と
  「どのリソースにも一致しなかった」を失敗にする。

## 5. 拡張ポイント

| 拡張 | 実装するもの | Kernel に渡す場所 |
|---|---|---|
| Retriever | `Retriever.search(registry, query)` | `retriever=` |
| Selector | `SetSelector.select(results, *, context)`（任意で `default_limits`、`min_score`） | `selector=` |
| LLM | `LLMProvider.complete(messages, tools)` | 位置引数 `llm` |
| 埋め込み | `EmbeddingProvider.embed(texts)` | `HybridRetriever` / `HierarchicalRetriever` / `CaseBasedRouter` 経由 |
| Cross-encoder | `CrossEncoderProvider.score` | `CrossEncoderRerankRetriever` 経由 |
| グルーピング | `GroupingStrategy.partition` | `HierarchicalRetriever` 経由 |
| Connector | `Connector.tools()` | `connectors=`（registry と handler に自動統合） |
| MCP | `connect_mcp_server` の resources / implementations | registry と `tool_implementations=` |
| ポリシー | `PolicyGateway` または `SafetyInspector` のサブクラス（ルール専用の ABC は無い） | `gateway=` |
| HITL | `HitlBroker._ask` | `hitl=` |
| Planner | `Planner.plan` / `replan` | `planner=` |
| State | `StateStore` の 5 フック（`_read_events`、`_write_event`、`task_ids`、`_read_session`、`_write_session`） | `state_store=` |
| Secret | `SecretResolver.resolve` | `secret_resolver=` |

研究用の新手法は、この表のどれかとして実装し、`Kernel` の既定値を変えずに差し込める形を
優先する。`CaseBasedRouter`（案F）と `ExecutionEvaluator` は Kernel の外で合成する
コンポーネントであり、Kernel に組み込む場合は ADR を起こす。

## 6. 設定

実行時に読まれる環境変数の正本は `.env.example`。`scripts/check_env_documentation.py`
がコードとの同期を検証する。

| 変数 | 読む場所 |
|---|---|
| `ANTHROPIC_MODEL`（必須）、`ANTHROPIC_API_KEY`、`ANTHROPIC_MAX_TOKENS`（必須・正の整数） | `providers.py` |
| `OPENAI_MODEL`（必須）、`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_REASONING_EFFORT` | `providers.py` |
| `OPENAI_EMBEDDING_MODEL`（必須）、`OPENAI_API_KEY`、`OPENAI_BASE_URL` | `semantic.py` |
| `MARMO_NOTIFICATION_<DESTINATION>_URL` | `sample_resources/tools.py` |
| `BENCHMARK_EMBEDDING_MODEL`、`BENCHMARK_CROSS_ENCODER_MODEL` | `benchmarks/run_benchmark.py` |

`EnvironmentSecretResolver` が読む変数名は利用者が決めるため対象外。`ShellConnector`
は許可リスト（既定 `PATH`）にある環境変数だけを子プロセスに渡す。

## 7. リポジトリ構成

- `marmo_core/`: ライブラリ本体（上表）。`py.typed` 同梱、`mypy` の対象。
- `tests/`: `unittest`。モジュールとの対応は `docs/knowledge/development_conventions.md`。
  `tests/fixtures/compat/` は互換性契約の凍結物、`tests/fake_mcp_server.py` は MCP テスト用。
- `resources/memory|tools|agents/`: 同梱サンプル各 10 件。実行可能で、テストに含まれる。
  `resources/skills/` は git 管理外のサードパーティコーパス（`benchmarks/README.md`）。
- `examples/`: README と対応する実行例。`tests/test_v2_examples.py` が別プロセスで実行する。
- `benchmarks/`: ルーティング・集合選択・スケール・適応の各スイート、シナリオ、
  コミットされた結果 JSON、`_provenance.py`（結果に commit SHA を刻む）。
- `scripts/`: CI が呼ぶ検査（`release_check.py`、`check_doc_paths.py`、
  `check_env_documentation.py`）。sdist と Docker イメージに同梱される。
- `tools/`: 開発者専用（skill コーパスの収集）。配布物には入れない。
- `docs/`: 利用者向けマニュアル（`connectors.md`、`local-resource-packages.md`）、
  脅威モデル、`knowledge/`、`decisions/`。
- `.github/`: CI / Release ワークフロー、Dependabot、ブランチ保護の記録、PR テンプレート。
