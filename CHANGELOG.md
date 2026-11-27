# Changelog

All notable changes to this project are documented in this file. New entries include
an English description and a Japanese description.

このファイルにはプロジェクトの主な変更を記録します。今後の項目は英語と日本語で記載します。

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Raise the minimum supported Python version to 3.11 following the end of
  upstream support for Python 3.10.
  - Python 3.10 の upstream サポート終了に伴い、最低対応バージョンを 3.11 に引き上げました。

- A second `Kernel.run` / `resume` of a task that is already executing now
  raises `StateConflictError` before any side effect. `JsonFileStateStore` and
  `SQLiteStateStore` exclude other instances and processes with OS file locks
  (lock files under `locks/` in the state directory, or `<db>.locks/`); a custom
  `StateStore` excludes within one instance unless it implements
  `_execution_guard`. See ADR 0015.
  - すでに実行中のタスクへの二つ目の `Kernel.run` / `resume` は、副作用の前に
    `StateConflictError` になります。`JsonFileStateStore` と `SQLiteStateStore` は OS の
    ファイルロック（状態ディレクトリの `locks/`、または `<db>.locks/`）で他のインスタンスと
    プロセスも排他します。独自の `StateStore` は `_execution_guard` を実装しない限り、
    同一インスタンス内だけを排他します。ADR 0015 を参照してください。
- A model reply cut off at the output limit (`finish_reason=length`) ends the
  task as `failed` instead of `completed`; the partial text stays in `output`.
  - 出力上限で打ち切られたモデル応答（`finish_reason=length`）は、`completed` ではなく
    `failed` で終わります。途中までの出力は `output` に残ります。
- `marmo run --audit-log` appends to an existing audit log after verifying its
  chain instead of replacing the file; a broken chain or a file another writer
  changed is refused with exit code 2. `--tool-args` is parsed and counted by
  `--strict` only with `--llm mock` or `--planner rule`. Non-object
  `--tool-args` values, unloadable `--tool-impl` / `--agent-impl` modules, and
  an empty `--modify` exit 2 with a diagnostic (previously a traceback with
  exit 1, or a silent defer).
  - `marmo run --audit-log` は既存の監査ログを置換せず、チェーンを検証して追記します。
    壊れたチェーンや他の書き手が変更したファイルには書き込まず、終了コード 2 で終わります。
    `--tool-args` は `--llm mock` または `--planner rule` のときだけ解析し、`--strict` の
    判定に含めます。値が object でない `--tool-args`、読み込めない `--tool-impl` /
    `--agent-impl`、空の `--modify` は診断付きの終了コード 2 になります（以前はトレース
    バックと終了コード 1、または保留）。
- A dependency written as `id@version` names that version only, and a bare id
  shared by several versions is ambiguous and resolves to nothing, in graph
  expansion, every set selector, the rule-based planner, and Connector handler
  registration (`connector_implementations` / `install_connectors` key such
  handlers by `id@version`).
  - 依存参照の `id@version` はその版だけを指し、複数版が共有する裸 ID は曖昧として解決
    しません。グラフ拡張、各集合選択、ルールベース Planner、Connector のハンドラー登録
    （`connector_implementations` / `install_connectors` は該当ハンドラーを `id@version`
    キーで返す）で共通です。
- Resource JSON: `extras` and `source` as written by `ResourceDefinition.to_dict()`
  are unwrapped on load, and an input schema `type` outside the supported set is
  a validation error instead of being ignored. Embedding and chat providers
  raise `ProviderError` for a 200 response that is not the expected JSON
  (previously `JSONDecodeError`, `KeyError`, or `ValueError`).
  - リソース JSON の `extras` と `source`（`ResourceDefinition.to_dict()` の出力形）を
    読み込み時に展開します。入力スキーマの対応外の `type` は無視せず検証エラーにします。
    埋め込み・チャットのプロバイダーは、期待した JSON でない 200 応答に `ProviderError` を
    送出します（以前は `JSONDecodeError`、`KeyError`、`ValueError`）。
- `ExecutionOutcome.resource_ids` read from an audit log carry `id@version`, and
  `ExecutionEvaluator` credits outcomes to the selected version only; the keys
  of `ExecutionEvaluator.snapshot()` and `report()` follow (`stats_for` and
  `attempts` still accept a bare id).
  The sdist no longer ships `tools/`. Releases to PyPI happen only on a pushed
  `v*` tag after the full CI passes on that commit; manual runs publish to
  TestPyPI only.
  - 監査ログから読んだ `ExecutionOutcome.resource_ids` は `id@version` になり、
    `ExecutionEvaluator` は実績を選ばれた版にだけ帰属させます。`snapshot()` と `report()` の
    キーも同じ形になります（`stats_for` と `attempts` は裸 ID でも引けます）。sdist は `tools/` を
    含みません。PyPI への公開は `v*` タグの push で、そのコミットの CI 全体が成功した
    場合に限ります。手動実行は TestPyPI のみです。

### Added

- `benchmarks/run_toolret_sae.py` adds ToolRet-SAE, which scores select,
  escalate, and abstain decisions on ToolRet: each query gets a variant with
  the gold tools permitted, one with only their scopes withheld, and one with
  them removed, and an annotator model labels which candidates could stand in
  for each gold tool. It ships a frozen held-out split (852 query ids outside
  the dev / test sample), the labels for 2,089 queries (ToolRet ids and
  judgments only, CC0 1.0), agreement with a second annotator (kappa 0.79 to
  0.88, both Claude models; no human validation), and a measurement showing
  that counting a labelled substitute as its gold tool raises nDCG@10 from
  0.266 to 0.437. See the ToolRet-SAE section of `benchmarks/README.md`.
  - ToolRet 上で選択・エスカレート・棄権の判断を採点する ToolRet-SAE
    （`benchmarks/run_toolret_sae.py`）を追加しました。各クエリから、正解ツールに権限がある
    変種、スコープだけ未付与の変種、正解を削除した変種を作り、アノテータのモデルが正解ツールの
    代わりになる候補を判定します。固定した held-out 分割（標本に含まれない 852 件の ID）、
    2,089 クエリのラベル（ToolRet の ID と判定のみ、CC0 1.0）、第 2 アノテータとの一致度
    （κ 0.79〜0.88。どちらも Claude 系で、人による検証はなし）、代替を正解に含めると nDCG@10 が
    0.266 から 0.437 に上がるという測定を含みます。`benchmarks/README.md` の「ToolRet-SAE」節を
    参照してください。

- `Kernel(gate_aware_selection=True)` and `SelectionContext.policy` hand the
  activation gate's policy to the selector. The rule-based, greedy, beam,
  branch-and-bound, and coverage selectors then leave out every candidate the
  gate denies whatever is granted or approved (a trust level or side effect
  outside the policy, an isolation level that is unavailable or too low): it is
  not selected in place of a usable resource and is not a reason to escalate,
  and the selection reason names it. Missing permissions still escalate. Off
  by default, so existing selections do not change. With it on, a Tool that
  forges only part of its declarations is selected in 3% of benchmark variants
  instead of 23%, and the legitimate Tool is lost in 17% instead of 37%; one
  labelled escalate case becomes abstain because its Tool needs an isolation
  level the default runtime lacks. `policy.static_denials` exposes the check.
  See ADR 0014 and `benchmarks/README.md`.
  - `Kernel(gate_aware_selection=True)` と `SelectionContext.policy` で、activation gate の
    方針を Selector に渡せるようにしました。rule-based・greedy・beam・分枝限定・被覆型の各
    Selector は、権限や承認にかかわらずゲートが拒否する候補（許可されない信頼度・副作用、
    使えない・水準に満たない隔離レベル）を、利用できる資源の代わりに選ばず、escalate の理由にも
    しません。外した候補は選択理由に出ます。権限不足は従来どおり escalate します。既定はオフで、
    既存の選択結果は変わりません。オンにすると、宣言の一部だけを偽装した Tool が選ばれる割合は
    ベンチマークで 23% から 3% に、正規の Tool が渡らなくなる割合は 37% から 17% に下がります。
    一方、escalate がラベルの 1 ケースは、Tool が既定の実行環境に無い隔離レベルを要求するため
    abstain に変わります。判定は `policy.static_denials` で参照できます。ADR 0014 と
    `benchmarks/README.md` を参照してください。

- `benchmarks/run_forgery_benchmark.py` tracks how far a resource with forged
  declarations gets: for Tool, Skill, and Agent decoys, each forged
  declaration (trust, permissions, side effect, isolation) and every
  combination of them, it reports the selection rate, activation-gate pass
  rate, whether `Kernel.run_goal` hands the decoy to the model, and whether a
  call reaches an inert stand-in handler through the execution gate, plus
  displaced gold resources and hijacked abstain/escalate decisions. The six
  legacy cases (`metadata_forgery` 6/6) are re-measured as the baseline. With
  the greedy selector a fully forged Tool reaches the model in 53% of its 88
  task variants, and no partial forgery passes activation. See
  `benchmarks/results/forgery.json` and `benchmarks/README.md`.
  - 宣言を偽装したリソースがどこまで届くかを測る `benchmarks/run_forgery_benchmark.py` を
    追加しました。Tool・Skill・Agent の偽装資源について、信頼度・権限・副作用・隔離レベルの
    各宣言とその全組み合わせごとに、選択率、activation gate の通過率、`Kernel.run_goal` が
    モデルに渡すか、呼び出しが execution gate を通って何もしない代替ハンドラに届くかを測り、
    正規の資源の押しのけと abstain / escalate の乗っ取りも記録します。従来の 6 件
    （`metadata_forgery` 6/6）を基準線として同じ実行で再測定します。greedy では、全偽装の
    Tool が 88 変種の 53% でモデルに届き、一部だけの偽装は activation を通りませんでした。
    `benchmarks/results/forgery.json` と `benchmarks/README.md` を参照してください。
- `EmbeddingProvider.embed_queries()` embeds search queries. It defaults to
  `embed()`; providers for asymmetric retrieval models (BGE, E5,
  Arctic-Embed, Nomic), which expect an instruction on the query side only,
  override it. `HybridRetriever` and `HierarchicalRetriever` now embed goals
  through it and resources through `embed()`. Providers that only define
  `embed()`, including ones that do not subclass `EmbeddingProvider`, behave
  as before. On ToolRet, dropping Arctic-Embed-S's query instruction costs
  0.065 nDCG@10 in dense retrieval (95% CI [0.056, 0.074]). The ToolRet
  benchmark takes `--query-prefix` for such models and `--records` for
  per-query metrics; `benchmarks/compare_toolret_records.py` pairs two runs.
  - 検索クエリ用の `EmbeddingProvider.embed_queries()` を追加しました。既定は `embed()` と
    同じです。クエリ側にだけ指示文を付ける非対称な検索モデル（BGE、E5、Arctic-Embed、Nomic）
    のプロバイダは、これを上書きします。`HybridRetriever` と `HierarchicalRetriever` は、
    ゴールをこのメソッドで、リソースを `embed()` で埋め込みます。`embed()` だけを持つ
    既存のプロバイダ（`EmbeddingProvider` を継承しないものも含む）はこれまでどおり動きます。
    ToolRet では Arctic-Embed-S の指示文を外すと dense 検索の nDCG@10 が 0.065
    （95% CI [0.056, 0.074]）下がりました。ToolRet ベンチマークに `--query-prefix` と
    `--records` を、2 回の実行を対応づけて比べる `benchmarks/compare_toolret_records.py` を
    追加しました。
- Added English and Japanese editions of the linked user guides, architecture
  and decision records, benchmark documentation, and contributor and security
  guides. Each language in the README links to its corresponding guides.
  - README の各言語から、利用ガイド、アーキテクチャと設計判断、ベンチマーク、
    貢献・セキュリティ関連の各言語版を読めるようにしました。
- Set `MARMO_CLI_LANGUAGE=ja` in the process environment for Japanese CLI help,
  input diagnostics, and main task output labels. English remains the default.
  - プロセスの環境変数 `MARMO_CLI_LANGUAGE=ja` を設定すると、CLI のヘルプ、
    入力エラー、タスク結果の主なラベルを日本語で表示します。既定は英語です。

### Fixed

- `LLMSetSelector` reads the last JSON object in a reply instead of everything
  between the first `{` and the last `}`. A model that follows its answer with a
  corrected object used to make the reply unparseable, and the selector then
  fell back to every candidate id mentioned in the text, including retracted
  ones; a corrected `abstain` came back as `selected`. The prompt and request
  are unchanged, so cached replies replay with only their interpretation changed.
  - `LLMSetSelector` が、最初の `{` から最後の `}` までではなく、応答中の最後の JSON
    オブジェクトを読むようにしました。答えのあとに訂正版を続けるモデルでは、応答を
    JSON として読めなくなり、撤回した ID を含む本文中のすべての候補 ID を選んでいました。
    訂正後の `abstain` も `selected` になっていました。プロンプトとリクエストは変えて
    いないので、キャッシュ済みの応答は解釈だけが変わって再生されます。

- A task interrupted between saving a Tool result and saving the continuation
  no longer runs that Tool again when another Kernel resumes it: calls are
  journaled by id, a recorded result is continued from, and a call with only a
  start on record is reported as an unknown outcome and waits for a person
  instead of being retried.
  - Tool の結果を保存してから続きの位置を保存するまでの間に中断したタスクを別の Kernel が
    再開しても、その Tool を再実行しなくなりました。呼び出しを ID ごとに記録し、結果が
    残っていればそこから続けます。着手の記録しかない呼び出しは結果不明として扱い、
    再試行せず人の判断を待ちます。
- `cancel()` during a model or Tool call is no longer overwritten by the late
  result, and no further call starts after it.
  - モデルや Tool の呼び出し中の `cancel()` が、遅れて届いた結果で上書きされなくなりました。
    キャンセル後は新しい呼び出しを始めません。
- Plans obey `max_tool_calls` (also across parallel waves and pauses), and a
  step whose outcome is unknown (timeout) is no longer re-planned around.
  - Planner 経路も `max_tool_calls` に従います（並行実行と一時停止をまたいでも同じ）。
    結果不明（timeout）のステップを避けて自動で再計画することはなくなりました。
- Arguments a reviewer edits with `modify` on a planned step are validated,
  stored on that step, and used when the task resumes; invalid edits raise
  `HitlError` and leave the request pending. When parallel steps pause
  together, the returned request is the one stored for resume (the first paused
  step in plan order); the others ask again after it is answered.
  - Planner のステップに対して `modify` で修正した引数を検証し、そのステップに保存して、
    再開時に使うようにしました。不正な修正は `HitlError` になり、依頼は保留のまま残ります。
    並行するステップが同時に一時停止した場合、返却する依頼と保存される依頼が一致します
    （プラン順で最初のステップ）。残りは、その回答のあとに改めて依頼します。
- Budget reservations made through two connections to the same store can no
  longer both pass the balance check; `JsonFileStateStore` writes are atomic
  across instances.
  - 同じストアへの二つの接続からの予算予約が、両方とも残高確認を通ることはなくなりました。
    `JsonFileStateStore` の書き込みはインスタンスをまたいで原子的です。
- Projecting a log with many rollbacks is linear instead of replaying earlier
  rollbacks recursively. The Kernel checks whether the catalog is empty without
  listing it, and `HierarchicalRetriever` keeps sub-registries across stats
  writes so a hybrid base does not re-embed documents after every task.
  - rollback を多く含むログの投影を、過去の rollback を再帰的に再生しない線形の処理に
    しました。Kernel はカタログを列挙せずに空かどうかを判定し、`HierarchicalRetriever` は
    統計の書き戻し後も部分レジストリを保持するため、hybrid 基盤がタスクごとに文書を
    再埋め込みしなくなりました。
- Beam search merges routes that share a dependency and charges shared members
  once. A replan that renames a colliding step also rewrites the `depends_on`
  of later new steps. `GoalAwareSetSelector` searches `context.one_of`
  alternatives against the final root relevance checks, and a TaskSpec node
  declaring both `all_of` and `one_of` is reported as ambiguous.
  - Beam Search は依存を共有するルートを併合し、共有メンバーを一度だけ数えます。ID 衝突で
    ステップを改名する再計画は、後続の新ステップの `depends_on` も更新します。
    `GoalAwareSetSelector` は `context.one_of` の代替を最終検証のルート条件で探索し、
    `all_of` と `one_of` が同居する TaskSpec のノードを曖昧として診断します。
- Retrieval slots are no longer used up by candidates under the score floor or
  outside a kind filter (`KindBalancedCandidatePool`, `HybridRetriever`,
  `HierarchicalRetriever`). `LLMRerankRetriever` drops duplicate ids before
  truncating, `CrossEncoderRerankRetriever` applies the score floor and
  per-kind limits to a lone candidate, and `CoverageSetSelector` treats results
  ranked without decomposition as goal-facet matches.
  - 下限未満の候補や種類フィルター対象外の候補が検索枠を使い切らなくなりました
    （`KindBalancedCandidatePool`、`HybridRetriever`、`HierarchicalRetriever`）。
    `LLMRerankRetriever` は件数を切る前に重複 ID を除き、`CrossEncoderRerankRetriever` は
    候補一件でも下限と種類別上限を適用し、`CoverageSetSelector` は分解されなかった結果を
    ゴール facet として扱います。
- `CaseBasedRouter` re-checks the current query filters and set constraints on
  a cache hit and falls back to the pipeline on a violation.
  `ExecutionEvaluator` does not count a task paused for approval as a failure.
  - `CaseBasedRouter` はキャッシュヒット時にも現行の検索フィルターと集合制約を検証し、
    違反すれば通常のパイプラインに戻ります。`ExecutionEvaluator` は承認待ちのタスクを
    失敗に数えません。
- The MCP stdio client reads every complete message that arrives in one write
  and applies one deadline to the whole request. Nullable type arrays such as
  `["string", "null"]` work in default-argument generation and validation.
  - MCP stdio クライアントは、同じ書き込みで届いた複数の完全なメッセージをすべて処理し、
    リクエスト全体に一つの期限を適用します。`["string", "null"]` のような型配列を既定値
    生成と引数検証で扱えるようにしました。
- The resume command printed on a pause includes `--responder` when
  `--approver` is set and keeps `--` before resource paths that start with `-`.
  `marmo list` / `search` tables shorten and align by terminal display width,
  so long Japanese descriptions keep their opening.
  - 一時停止時に表示する再開コマンドは、`--approver` 指定時に `--responder` を含み、`-` で
    始まるリソースパスの前の `--` を保ちます。`marmo list` / `search` の表は端末の表示幅で
    短縮・整列するため、長い日本語の説明も冒頭が残ります。
- Benchmarks: ToolRet paired differences and bootstrap intervals use the same
  subset-equal (macro) weighting as the tables, with the query-equal difference
  reported separately (published tables keep the earlier values, now annotated,
  until re-measured). ToolRet-SAE `score` accepts the published labels
  (`--labels-input`), matches cached replies by candidate ids and order, and
  exits non-zero when inputs are missing. Results carry `metric_version`
  (version 2 adds actionable-escalation scoring), and the overlap between the
  SAE held-out split and the earlier full test split (431 of 852) is
  documented. Results record the full commit, dataset revisions, input hashes,
  models, and arguments; ToolRet downloads are pinned to dataset commits.
  - ベンチマーク: ToolRet の対応差とブートストラップ区間を、表と同じサブセット等重み
    （macro）で計算し、クエリ均等の差を別に併記します（公開表は再測定まで以前の値のままで、
    その旨を注記）。ToolRet-SAE の `score` は公開ラベル（`--labels-input`）で採点でき、
    キャッシュを候補 ID と順序で照合し、入力が欠けると非ゼロで終了します。結果に
    `metric_version` を記録し（版 2 は実行可能な承認要求の採点を追加）、SAE の held-out と
    過去の全件 test の重複（852 件中 431 件）を文書に記録しました。結果には完全なコミット、
    データセット revision、入力ハッシュ、モデル、引数を記録し、ToolRet の取得先を
    データセットの commit に固定しました。
- Repository tooling: skill collection pins each source to a resolved commit
  and records only verified, complete downloads into `resources/skills`; the
  parallel-execution example no longer judges success by a wall-clock
  threshold; the doc-link check covers root-level links and the environment
  check parses Python instead of matching text; CI smoke-tests the built wheel
  and runs the Exact/HNSW index tests without skips; `.env` files are excluded
  from the Docker build context.
  - リポジトリのツール: Skill 収集は各収集元を解決済みのコミットに固定し、検証できた完全な
    取得だけを `resources/skills` に記録します。並行実行サンプルは成功を壁時計の閾値で判定
    しません。文書リンク検査はルート直下のリンクも検証し、環境変数検査はテキスト照合では
    なく Python を解析します。CI はビルドした wheel の smoke test と、スキップなしの
    Exact/HNSW インデックスのテストを実行します。Docker のビルドコンテキストから `.env` を
    除外しました。
- `marmo` accepts resource paths written after an option, in any order
  (`marmo inspect ID --format json PATH`, `marmo run PATH --task T PATH2`).
  These were rejected as `unrecognized arguments`: on Python 3.11 for every
  command, and on newer versions whenever an option split two paths. Unknown
  options are still errors.
  - `marmo` は、オプションの後ろに書いたリソースパスを順序によらず受け付けます
    （`marmo inspect ID --format json PATH`、`marmo run PATH --task T PATH2`）。これまでは
    `unrecognized arguments` になっていました（Python 3.11 ではすべてのコマンドで、それ以降の
    版でもオプションがパスを分断する場合）。未知のオプションは従来どおりエラーです。

## [0.7.0] - 2026-11-24

### Changed

- `LexicalRetriever` scores matches in descending order of an upper bound on
  their composite score and stops once the bound cannot reach the last result
  it returns. The ranking, scores, and reasons are those of the full scan
  (checked against it on 280 ToolRet queries and five query shapes, and by a
  new equivalence test). On the 44,453-tool ToolRet corpus, full scoring of
  every document that shares a query term was 90% of the search time; a query
  now fully scores about 1% of its matches, and warm latency fell from
  p50 85.8 ms / p95 512 ms / mean 143 ms to 36.6 ms / 262 ms / 82.7 ms.

- The Kernel now makes every selected set dependency-closed and conflict-free,
  whatever the selector. It adds declared dependencies from the candidate pool
  or the registry, and drops a resource whose dependency is missing, ambiguous,
  or denied at activation, or that conflicts with a higher-ranked member.
  Dropped resources appear in `skipped_resources` (so `--strict` fails) and in
  the `retrieve` audit record as `constraint_drops`. The default rule-based
  selector and `LLMSetSelector` used to hand such sets to the model unchanged.
  The Kernel's default compiler is now `ContextCompiler(preserve_dependencies=True)`
  for every selector, so a resource whose dependency was skipped at activation
  or would be cut by the token budget stays out of the context. Passing a
  `compiler` keeps the previous behaviour available.

- `GreedyConstrainedSetSelector`, `BeamSearchSetSelector`, and
  `BranchAndBoundSetSelector` now escalate when a unit blocked only by missing
  permissions has a higher utility than every unit in the feasible set and
  would fit the budgets on its own. They used to escalate only when nothing
  else was feasible, so a lower-ranked alternative was returned as a clean
  `selected` result. The escalation carries the blocked unit's
  `missing_permissions`. A blocked unit that ranks below the selected units is
  still reported as skipped.

- Semantic relevance is now cosine similarity clipped to [0, 1]. Negative
  cosines used to map to `(cosine + 1) / 2`, which ranked a cosine of -0.14
  above one of +0.14 in `HybridRetriever` and in `HierarchicalRetriever`'s
  group routing. Positive cosines, which real sentence embeddings almost
  always produce, score exactly as before.

- Provider responses without token usage now keep `LLMResponse.usage` empty
  instead of reporting zero tokens. Budgeted tasks charge the full reserved
  amount when usage is unknown.

- A timed-out Tool or Agent is no longer retried or replaced automatically.
  Its external effects may already have happened, so recovery asks for human
  reconciliation before another attempt. The `RetryPolicy` default now retries
  transient errors only.

### Added

- Opt-in multi-intent retrieval: `DecomposedRetriever` splits a goal into
  sub-tasks with a `QueryDecomposer`, searches the goal and every sub-task with
  an inner retriever, and fuses the rankings (default `fusion="blend"`:
  `(goal relevance + 0.25 x best sub-task relevance) / 1.25`). Each result
  carries its relevance to every sub-task as `facet.<i>` components. The goal's
  share is discounted by how many of its terms the catalog contains at all, so
  a Japanese goal over English tool descriptions is ranked by its (English)
  sub-tasks instead of by the few names and numbers it shares with the
  catalog (ToolRet, Japanese goals: nDCG@10 0.029 without decomposition,
  0.057 without the discount, 0.134 with it; English unchanged). The share is
  lexical, so pass `discount_unknown_terms=False` when a multilingual
  embedding model already reads the goal.
  `LLMQueryDecomposer` makes one model call per goal and names implicit
  prerequisites; on failure it logs a warning and searches the goal only.
  `ClauseQueryDecomposer` is a rule-based baseline: on ToolRet it did not
  improve the ranking (no significant difference over hybrid search, lower
  over BM25 alone) and is not recommended.
- Opt-in `CoverageSetSelector` chooses a set that covers the goal's facets
  (greedy facility location, counted per resource kind) and stops when another
  unit would add less than `min_gain` (default 0.1), so the set size follows
  the goal instead of a count limit. Without facet components it takes the
  best unit of each kind that clears `min_gain`. `include_within` also keeps
  near-ties of the top candidate for callers who would rather pass a model
  several near-equivalent tools (ToolRet, all 3,920 test queries: Set F1 of the
  top result 0.208, coverage 0.219, with `include_within=0.95` chosen on dev
  0.229). One more model call with `LLMSetSelector` chose better sets
  than either rule on ToolRet (0.243). Dependency closure, conflicts, permissions, budgets, and the
  abstain / escalate outcomes match `GreedyConstrainedSetSelector`.
- `function_tool_resources()` imports OpenAI, Anthropic, and MCP
  function-calling definitions as Tool resources (community trust, external
  side effect, and a `tools.<namespace>` permission by default; a name with no
  ASCII letters or digits gets a stable hashed id), and
  `examples/tool_catalog_routing.py` narrows 3,007 functions to the three a
  goal needs, offline.
- `benchmarks/run_toolret_benchmark.py` evaluates routing on the public ToolRet
  benchmark (44,453 tools, multi-tool gold sets; downloaded on demand, not
  redistributed; parquet reading needs the new benchmark-only
  `benchmark-toolret` extra, `pyarrow`), with dev/test splits and paired
  bootstrap intervals. Results
  are in `benchmarks/results/toolret.json` and the ToolRet section of
  `benchmarks/README.md`.

- Opt-in `DependencyExpandedCandidatePool` discovers declared metadata/context
  dependencies and all context alternatives up to a configurable bound. It keeps
  added relevance at zero, respects candidate policy denials, and reports overflow
  as `CandidatePoolLimitError`; after initial retrieval, the Kernel detects that
  before TaskSpec resolution or execution-model calls. An LLM-backed inner
  retriever can itself incur model calls before expansion. Existing defaults
  are unchanged.

- `Kernel(candidate_pool=...)` makes the construction of the selector's
  candidate list a replaceable component (`CandidatePool`,
  `CandidatePoolRequest`). `KindBalancedCandidatePool` is the default and
  keeps the Kernel's existing policy pre-filter and per-kind top-up.
  `RetrieverCandidatePool` hands the retriever's ranking over unchanged, so
  selectors can be compared through the Kernel without the top-up logic.

- Research opt-in goal-aware routing contracts and selection distinguish task
  effects from supporting context, and do not reward redundant resources by
  summing retrieval scores. Unknown declarations fail closed.
- `ContextCompiler(preserve_dependencies=True)` packs declared dependencies as
  complete units. Contract-aware Kernel routing verifies the activated payload
  and task sufficiency again before calling the model, including on resume.
  The `ContextCompiler` default is unchanged.

- `TopKSetSelector` (global Top-K with optional dependency expansion,
  conflict dropping, and a permission check) and `RepairingSetSelector`
  (the same repair applied to any selector's output), as baselines for the
  integrated constrained solvers.

- `LLMSetSelector(show_constraints=False)` omits dependency, conflict, and
  permission facts from the prompt. The default is unchanged.

- `LexicalRetriever(k1=..., b=...)` sets the BM25 parameters; the defaults
  (1.5 and 0.75) are unchanged.

- `RRFRetriever` fuses two retrievers' rankings with Reciprocal Rank Fusion.

- `HybridRetriever(vector_index=...)` takes a `VectorIndex` factory:
  `ExactVectorIndex` (numpy, exact) or `HNSWVectorIndex` (usearch HNSW,
  approximate). Without it the pure-Python similarity loop is unchanged.

- `BedrockLLMProvider` and `--llm bedrock` use the existing OpenAI-compatible
  Chat Completions implementation with `BEDROCK_API_KEY` (or
  `AWS_BEARER_TOKEN_BEDROCK`). Defaults to gpt-oss-120b in us-east-1; model,
  endpoint, region and reasoning effort can be configured in `.env`.
  OpenAI-compatible HTTP errors redact the exact configured API key.

- `LLMCatalogRetriever` ranks by showing the LLM the whole filtered catalog
  (id, kind, name, and the first `description_limit` characters of each
  description) with no candidate retrieval first. It is the baseline for
  measuring retrieve-then-rerank against, splits a catalog larger than
  `shard_size` into one call per shard plus a final ranking call, and reports
  `empty_replies` and `unknown_ids`. A reply may name candidates by id or by
  their number in the list.
- `LLMRerankRetriever` takes `description_limit` (default 240, the previous
  fixed value; `0` shows names only) and `accept_positions` (default `False`,
  the previous behavior), which reads a reply of list numbers as the
  candidates at those positions instead of ignoring it.

- `AgentRuntime` now dispatches through the public `AgentExecutionBackend`
  interface. The built-in `structured_task` backend runs a resumable child
  Kernel over an Agent's transitive declared dependencies, narrows its
  permissions to the Agent declaration, shares the parent task budget, and
  relays human approvals and modified arguments back to the child. Nested
  Agent depth and cumulative Agent cost now follow `max_agent_depth` and
  `max_agent_cost` instead of staying fixed at depth one.

- A task now persists its selected resources and their scores after routing.
  Resume restores that set without repeating retrieval or selection, and stops
  if a selected definition or the compiled execution context changed.

- `Kernel(task_budget=TaskBudget(...))` applies one explicit currency budget to
  selection, model calls, and every Tool or Agent attempt. Model calls reserve
  a configured token ceiling before dispatch and send the output-token ceiling
  in each provider request; input estimates include serialized messages and
  tool schemas. Resource estimates are reserved before execution. Reservations
  and settlements persist across retry, resume, and rollback.
  `Kernel.budget_status(task_id)` reports the remaining amount. Custom LLM
  providers must implement `complete_bounded()` and declare support for output
  token limits to be used with a task budget. Calls with missing usage or a
  provider exception are charged at the reserved ceiling.

- `ToolRuntime(timeout_mode="process")`, `Kernel(timeout_mode="process")`, and
  `marmo run --timeout-mode process` stop importable Python handlers when their
  deadline expires. A non-importable handler is rejected before execution in
  this mode. The existing thread mode remains the default for compatibility;
  it only limits how long the caller waits.

- Resuming a paused task restores its saved resource selection. Changes to a
  selected resource, loaded memory or skill text, or compiled context now fail
  the task instead of silently changing its execution snapshot. Legacy paused
  tasks that passed activation or execution without a saved snapshot fail closed.

- README now links to the Marmo Core website for the library overview, concepts,
  and usage guide.
- README now opens with an overview for readers evaluating the project: the
  request pipeline, layer, and task-lifecycle diagrams, real CLI output,
  the safeguards and their limits, design decisions with their decision
  records, measured results, and past failures with the check that now
  prevents each. The install and usage sections are unchanged.
- A held-out benchmark of bundled resources now reports real Tool execution
  success, artifact-checked single-step task completion, Layer 2 set quality,
  Layer 3 cache reuse, and adversarial metadata outcomes. A benchmark-only
  flat ANN comparison measures 100k routing against the hierarchical path.
- Two dependency-free repository checks run in CI next to `release_check.py`:
  `scripts/check_doc_paths.py` fails when the documentation names a
  repository path that no longer exists, and
  `scripts/check_env_documentation.py` fails when `.env.example` and the
  environment variables the library or the benchmarks read disagree.
  `.env.example` now documents `MARMO_NOTIFICATION_<DESTINATION>_URL`, the
  webhook variable the bundled `send-notification` sample reads.

## [0.6.0] - 2026-09-19

### Fixed

- The text-relevance component is absolute instead of rank-normalized, so a
  threshold on it means the same thing for every query. It used to be divided
  by the best BM25 score *in that result set*, which made the top hit of every
  query look like a strong match whether or not the catalog had anything to
  offer: against the bundled 1,000-skill corpus the goal 「私は今日ラーメンを
  食べたい気分です」 scored relevance 0.63 on a Step Functions visualizer
  skill, and the kernel activated it. Relevance is now measured against a
  document that names every query term once — 1.0 reads as "covers the whole
  query", and that goal scores 0.15. The yardstick is a per-query constant, so
  the only ranking it moves is between documents that beat the reference and
  tie at the clamp: measured against the same code with the old divisor,
  hit@5 and recall@20/@50 on the 120-scenario routing benchmark are identical
  and hit@1 costs two scenarios (66.7% -> 65.0%, MRR 0.702 -> 0.694). A gate
  that can distinguish a real match from the least-bad one is worth that.
- Retrieval indexes a resource's declared metadata and an attached SKILL.md
  body as two BM25F fields, with the body discounted (`BODY_FIELD_WEIGHT`).
  Indexing the body at full weight let a long document win on words its
  examples mention in passing: for "read a local text file safely" an
  XXE-scanner skill (7,551 indexed tokens) scored 0.79 against 0.58 for the
  file-reading Tool whose description is that sentence. The Tool now ranks
  first of all 1,030 resources, and on the routing benchmark hit@1 rises
  61.7% → 65.0% net of the two scenarios the clamp above costs (paraphrased
  wording 31% → 46%, abstract 48% → 55%) with recall@20 84% → 88%. With a
  model-backed hybrid retriever at the library's
  default `semantic_weight`, hit@1 rises 67% → 70% (bge-small) and
  68% → 73% (OpenAI embeddings).
- Writing execution stats back to the registry no longer rebuilds the inverted
  index or re-embeds the catalog. `ExecutionEvaluator.apply` rewrites `stats`
  on every observed resource, and both caches were keyed on
  `ResourceRegistry.revision`, so one feedback pass threw away work that did
  not depend on it: at 1,030 resources, re-tokenizing the catalog (0.9s) and
  re-embedding all 1,030 texts — a billed request per batch against a hosted
  embeddings endpoint. Verified against the real OpenAI endpoint: a search,
  a repeat search, and a stats write now cost 2 HTTP requests in total, where
  they cost 5 before. The hierarchical router's clustering and centroids and
  the capability graph are keyed the same way.
- Keyword filtering reads the index instead of rebuilding every candidate's
  full text. One keyword cost 22x the whole search at 1,000 resources
  (3.3ms → 74.9ms); it now costs 17.4ms.
- One goal issues at most two searches instead of one per starved kind. The
  per-kind top-up runs as a single kind-filtered, per-kind-limited search,
  which matters as soon as the retriever is embedding- or LLM-backed: each
  search was a separate paid round trip on the same goal string.
  `HybridRetriever` also caches query vectors (bounded by `query_cache_size`).
- `RuleBasedSetSelector` honours `SelectionContext.min_relevance`. Every other
  selector read the relevance floor; the one the kernel uses by default
  ignored it, so the gate that keeps an unrelated resource out of the compiled
  context did nothing in the default configuration.

### Added

- `Kernel(min_relevance=...)` passes an abstain floor to the selector. It
  defaults to 0.0: relevance is absolute now, so a floor is finally meaningful,
  but on the bundled corpus no single value rejects every off-topic goal
  without also rejecting real matches (measured: gold hits reach down to 0.13,
  the best off-topic hit reaches 0.52), so the number belongs to a deployment.
  At 0.4 on the bundled catalog, "read a local text file safely" compiles the
  one Tool it needs instead of 6,743 tokens of loosely related skills.
- `ResourceRegistry.content_revision`, which moves only when something
  retrieval reads changes, and `ResourceRegistry.count(kind)`, which answers
  "does this kind exist" without sorting the catalog.
- `LexicalRetriever.apply_limits` is public: the retrievers that wrap it
  re-rank a widened pool and then have to apply the caller's limits.

### Changed

- The benchmark scripts' `--min-relevance` default moves 0.55 → 0.35. Same
  operating point, new units: the old value was calibrated against the
  rank-normalized component.

## [0.5.0] - 2026-09-17

Everything under "Added" here was already on `main` but had never been
released: the published 0.4.0 predates real LLM providers, so a `pip install`
and a checkout reported the same version with very different behaviour. This
release separates them, and fixes what a full pass over the library with a
real model (Groq, OpenAI-compatible) turned up.

### Fixed

- Retrieval no longer lets one crowded kind starve the others. A single global
  `top_k` meant a catalog of a thousand Skills could take every candidate slot
  next to ten Tools, so the set selector reported `tool=0/3`, no callable ever
  reached the model, and the run still ended `completed`. Each kind that comes
  back short of its set limit now gets one kind-filtered search of its own.
- `marmo run --strict` fails when the registry holds Tools or Agents but none
  of them reached the model (`NO_CALLABLE_SELECTED_DETAIL`), instead of
  exiting 0 on an answer that could not have used a guarded call.
- The `marmo resume` command printed with a pause now repeats the flags the
  run was authorized with. Copying the old hint dropped
  `--granted-permission` and `--allow-side-effect`, so the approved tool
  failed its activation gate, was reported as "skipped", and the task still
  ended `completed` with exit 0.
- Tool arguments that fail the input schema go back to the model, which may
  call again (`--max-input-repairs`, default 2), rather than ending the task
  on the first mistake. The same applies when the model names a callable that
  is not available: it is told which ones are.
- A provider error ends the task as `failed` instead of escaping the kernel,
  so the audit log, the terminal task status, and any side effects already
  executed stay on record; `--audit-log` is now written even when the run
  raises. A crashed run no longer strands its task in `running`. Two
  consequences worth noting: `marmo run` exits 1 rather than 2 for a provider
  failure, and the provider's message is now recorded in the audit log and the
  task state rather than only printed.
- One tool result can no longer overflow the model's context.
  `--max-tool-output-tokens` (default 8000) truncates an oversized result and
  says so in the text; `context_token_budget` only ever bounded the compiled
  context, not what a tool handed back.
- Planned runs answer the goal again. `_finish_plan` sent the step results as
  `tool` messages with no assistant tool call to answer, which both the OpenAI
  and Anthropic APIs reject, so every plan fell back to the canned
  "Plan complete over N step(s)" summary.
- Pause messages name a remedy that actually works. The fixed wording always
  suggested `PolicyContext(human_approved=True)`, which deliberately does not
  clear a safety finding or an always-confirm rule -- the two escalations
  scoped to the exact reviewed call.
- `OpenAICompatibleEmbeddingProvider` honours `OPENAI_BASE_URL` like the chat
  provider does. It was pinned to `api.openai.com`, so a Groq/vLLM/Ollama
  setup sent its API key to OpenAI.
- Provider error bodies are redacted before they reach an exception message or
  a log line; a 401 from OpenAI echoes part of the key that was sent.
- A 401/403 with no API key configured says so, instead of only relaying the
  server's "invalid API key".
- `HydeRetriever`, `LLMRerankRetriever`, and `LLMSetSelector` still degrade
  gracefully when the model call fails, but now warn once through `logging`
  and keep the exception on `last_failure`. A misconfigured provider used to
  make `--retriever hyde` silently do nothing.
- SKILL.md frontmatter understands block scalars with chomping and
  indentation indicators (`>-`, `|-`, `>+`, ...). `description: >-` was read as
  the literal string `">-"` and the continuation lines became junk keys, which
  removed those skills from retrieval.
- A Markdown skill inside a local resource package derives its id inside the
  package namespace, so the layout documented in
  `docs/local-resource-packages.md` loads without an explicit `id:`.
- Malformed JSON found while scanning a directory is reported as a warning and
  named in `marmo validate`'s summary instead of being skipped in silence,
  which made a typo in a resource file read as "valid: 0 resources" with exit
  0. A directory scan cannot know which unparsable file was meant to be a
  resource, so the file is skipped rather than failing the load -- naming it
  explicitly still raises. Valid JSON that is not a resource definition is
  ignored as before, and a byte-order mark or a non-UTF-8 encoding no longer
  aborts the scan.
- Credential-shaped values are redacted from audit records, not only from keys
  whose *name* looks sensitive, so a provider message reaching the log through
  a custom transport cannot carry a key into the hash chain. The pattern set
  moved to `marmo_core.secrets` and grew the vendor shapes it was missing
  (`github_pat_`, `AIza…`, `xox[baprs]-`, `Basic …`), and a key carried in a
  URL query string is redacted too.
- The `marmo resume` hint masks credential-shaped values inside `--tool-args`,
  the one forwarded option that carries free-form payload rather than
  configuration.
- `.env.example` no longer ships `OPENAI_REASONING_EFFORT=none`, which Groq
  rejects with HTTP 400 on the first request of the documented setup.
- `benchmarks/run_benchmark.py` explains how to obtain the skill corpus
  instead of raising `ResourceLoadError` when it is absent, as it is in the
  sdist.

### Changed

- Filling the per-kind candidate slots means a goal can be offered a Tool that
  a crowded pool used to hide from it. The exposure is not new -- the same Tool
  is selected today in any registry small enough not to crowd, because no
  selector applies a relevance floor -- but removing the crowding removes the
  mask. Top-ups skip anything the activation gate would deny and honour a
  selector's `min_score`; the gates, the HITL escalation for side-effecting
  resources, and `set_limits` remain the controls.

### Added

- `Kernel(max_input_repairs=..., max_tool_output_tokens=...)` and the matching
  `marmo run` / `marmo resume` flags.
- `TaskResult.hitl` returns the pending confirmation as a `HitlRequest`, and
  `ResourceDefinition.id` / `.kind` read the common metadata fields directly.
- A note on stderr when `--retriever hyde` is paired with `--llm mock`, whose
  canned reply steers retrieval at random.

- Real providers can call tools again: resource ids contain dots
  (`tool.files.read-text`), which the OpenAI and Anthropic tool-name grammars
  reject. `AnthropicLLMProvider` and `OpenAICompatibleLLMProvider` now encode
  tool names on the wire through `ToolNameCodec` and map the model's calls back
  to the original ids, so the kernel and audit log keep seeing resource ids.
- `OpenAICompatibleLLMProvider` sends `max_completion_tokens` to `openai.com`
  (current OpenAI models reject `max_tokens`), keeps `max_tokens` for other
  OpenAI-compatible servers, and switches once if the server reports the chosen
  parameter as unsupported. `max_tokens_parameter` pins either name.
- Provider HTTP failures raise `ProviderHTTPError` with the status and the
  response body's message instead of a bare `urllib` `HTTP Error 400`, and
  network failures raise `ProviderError`.
- Provider requests carry a `marmo-core/<version>` User-Agent; gateways such as
  Groq's return 403 (Cloudflare error 1010) for urllib's default agent.
- When retrieval matches no resource and the model answers without tools, the
  completed `TaskResult.detail` now says so (`NO_RESOURCE_MATCHED_DETAIL`) and
  `marmo run --strict` treats it as a violation instead of a silent success.
- The compiled system prompt states explicitly when no tools are available, so
  models that would otherwise emit a spurious tool call (gpt-oss on Groq) answer
  directly instead of failing the request.

### Changed

- The default set limit for Tools is now 3 (Memory, Skill, and Agent stay at 1),
  so goals that need more than one tool (list files, then read one) can finish.
  Lower-ranked candidates the Policy Gateway would deny are left out of the
  set; the best match of each kind is still reported as skipped when denied.
- The HyDE rewrite prompt asks for English so goals stated in other languages
  (for example Japanese) match the English-documented registry.

### Added

- `marmo run --llm {mock,openai,anthropic}` runs a goal with a real provider
  configured from the environment or `.env`, and `--retriever {lexical,hyde}`
  rewrites the goal with that provider before lexical retrieval.
- `OPENAI_BASE_URL` selects any OpenAI-compatible endpoint (Groq, vLLM, Ollama)
  for `OpenAICompatibleLLMProvider` and `--llm openai`.
- `marmo --version`, and a hint on stderr when `list` or `search` finds no
  resource definitions.
- A Python quickstart in the README.

## [0.4.0] - 2026-08-16

First release published to PyPI.

### Added

- Unified resource model covering Memory, Tool, and Agent resources, with a
  registry, retriever, reranker, and selector for task-driven activation.
- `marmo` / `marmo-core` CLI with `validate`, `list`, `search`, and `run`
  commands, including `--strict` runs for automation and release gates.
- Guarded execution: permission declarations, exact side-effect allowlists
  (`--allow-side-effect`), policy evaluation, audit logging, secret handling,
  and human-in-the-loop approval.
- Built-in connectors and MCP support, plus an executable tool and agent
  runtime backed by `python:` refs.
- Thirty bundled resource samples (ten each for Memory, Tool, and Agent) that
  run against the standard library without manual binding.
- Provider configuration read from `.env` (`OPENAI_MODEL`, `ANTHROPIC_MODEL`,
  `OPENAI_EMBEDDING_MODEL`, and related settings) instead of hard-coded
  defaults.
- Typed distribution (`py.typed`) and an optional `benchmark` extra for the
  embedding and cross-encoder integration.

[Unreleased]: https://github.com/kota-kawa/Marmo-Core/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/kota-kawa/Marmo-Core/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/kota-kawa/Marmo-Core/releases/tag/v0.6.0
[0.5.0]: https://github.com/kota-kawa/Marmo-Core/releases/tag/v0.5.0
[0.4.0]: https://github.com/kota-kawa/Marmo-Core/releases/tag/v0.4.0
