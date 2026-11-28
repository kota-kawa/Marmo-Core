# Marmo-Core Agent Rules

Marmo-Core は、Object Routing を実装する公開 Python ライブラリである。
このファイルは、このリポジトリで作業するエージェント（と人間）の規約をまとめる。

## この文書の読み方

- 最重要の原則は、研究速度のために公開ライブラリの安定性を壊さないこと。一方で、研究用ブランチでは新しい手法を積極的に試してよい。
- 「守る境界」は、壊すと利用者・他の作業・再現性に被害が出るものであり、例外なく守る。
- それ以外の節は、理由を添えた既定の進め方である。調べ方、設計、実装の組み立て、作業の順序は自分で判断してよい。既定と違うやり方のほうが目的に合うと判断したら、そうしたうえで、変えた点と理由を報告に書く。
- ここには、コードを読んでも分からない制約と理由、そして参照先だけを書く。手順の細部は参照先の文書にあるので、必要になった文書の必要な章を読む。

## 守る境界

- **`main` は安定版で、PyPI に公開される。** 直接 push せず、すべての変更を作業ブランチにコミットして PR で取り込む。エージェントは、ユーザーから明示的な指示がない限り PR をマージしない。
- **このリポジトリが実装コードの唯一の正である。** `Object-Routing-Research` へ Marmo-Core 本体をコピーしない。評価はそちらから commit SHA を固定して行う。
- **研究中の手法は `research/<method-name>` ブランチに置く。** 実験で有効性を確認できるまでは `main` に入れず、`Kernel` の既定挙動も変えない。
- **他者の成果物を壊さない。** ユーザーまたは他のエージェントによる既存の変更を、明示的な許可なく上書き、破棄、巻き戻ししない。`benchmarks/results/` に未追跡の結果ファイルがあることが多いが、他の作業の成果物なので、触らず、自分のコミットにも含めない。
- **利用者に見える表面を変える判断は、着手前にユーザーと合意する。** 対象は公開 API、既定値、CLI 終了コード、リソース定義、状態ファイル、監査ログ、スコアの尺度。依頼の解釈が分かれて結果が大きく変わる場合も同じ。合意していない変更は加えない。
- **実行時依存は確認なしに増やさない**（現在は `python-dotenv` の 1 つ）。追加する前に、必要性、標準ライブラリや既存の依存で代替したときのコスト、インストールサイズ・推移的依存・ライセンスへの影響をユーザーに示し、確認を取る。確認なしに `pyproject.toml` の `dependencies` を変更しない。ベンチマークや開発だけに要るものは `benchmark` / `dev` extra に置く。追加した場合は理由と影響を PR に書く（`docs/decisions/0007-minimal-runtime-dependencies-with-user-approval.md`）。
- **凍結物は書き換えない。** `tests/fixtures/compat/v0.3.0/` は互換性契約の凍結物であり、新しい契約を凍結するときは新しいバージョンのディレクトリを追加する。`benchmarks/results/*.json` はコミットされた測定結果であり、実装を変えずに数値だけを変更しない。再測定したら同じ PR で実装差分と一緒に更新し、`benchmarks/README.md` の数値も揃える。
- **秘密と再配布できないものを外に出さない。** `.env` には秘密情報が入るため、その内容を読んだり、ログ・文書・報告へ転記したりしない（環境変数の一覧は `.env.example` を読む）。シークレットは環境変数または `.env` に保持し、git に含めない。`resources/skills` はサードパーティのコーパスで、再配布しない。git と sdist の両方から除外されている。
- **信頼境界を黙って動かさない。** 権限、副作用分類、ポリシー評価、シークレット処理、HITL ゲートに触る変更は `docs/threat-model.md` に照らしてレビューし、境界を動かしたら同文書を更新する。
- **実装したエージェントは自分で完了判定をしない。** PR を作る前に「テストと検証」の全体検査を通し、コードを変更する PR は「レビュー」の手順でレビューを受ける。

## ドキュメントの参照先

各行は「パス／内容の区分／いつ参照するか、または何に使わないか」の型で書く。

- `README.md`／公開向けの概要・インストール・Quickstart・CLI と `.env` の使い方／利用者視点の説明を確認・修正するとき。内部設計の正本としては扱わず、実装との差分が見つかった場合は公開向け説明として修正する。
- `ARCHITECTURE.md`／レイヤー構成、`Kernel.run_goal` と CLI のリクエスト経路、契約と境界、拡張ポイントをまとめた内部設計の正本／複数モジュールにまたがる変更で、必要な章を読む。
- `docs/knowledge/development_conventions.md`／プロジェクト構成、ビルド・テストコマンド、実装規約、命名、責務分割、テスト方針、サブエージェントの指定、AI 出力の品質確認／コードを変更する作業の規約の正本。該当する節を着手前に確認する。
- `docs/knowledge/README.md`／再利用可能な知見の索引／調べ物の出発点。作業ログや一時的な状態は追加しない。
- `docs/knowledge/debugging.md`／実モデル・検索・CLI・パッケージングの不具合の切り分け手順／動作がおかしいときの最初の手がかり。
- `docs/knowledge/contracts-and-compatibility.md`／公開 API、リソース定義、状態ファイル、監査ログ、CLI 終了コードの互換性契約と変更手順／これらの表面に触る変更の前に読む。
- `docs/knowledge/parallel_work.md`／サブエージェントと git worktree で作業を分ける判断基準と、分けた後の運用手順／並行作業をするときに読む。
- `docs/knowledge/experiment_runbook.md`／実験の段取り、評価設計の約束、Claude Code クラウドセッションとローカル PC での LLM・計算資源・長時間ジョブの扱いの違い／ベンチマークや評価実験を始める・再開する前に読む。
- `docs/knowledge/lessons_from_history.md`／git 履歴と PR から抽出した過去の失敗と教訓／同じ轍を踏まないために、該当領域を触る前に読む。
- `docs/task-sufficient-routing.md`／研究用の要求充足・集合選択・最終文脈検査の契約と制限／GoalAwareSetSelector と依存保持 compiler を利用・変更するとき。
- `docs/threat-model.md`／信頼境界・想定脅威・リリース前レビューの記録／権限、副作用、ポリシー、シークレット、HITL に触る変更で読む。
- `docs/connectors.md`、`docs/local-resource-packages.md`／利用者向けマニュアル／実装の責務や内部挙動を確認する資料としては使わない。
- `benchmarks/README.md`／ベンチマークの実行方法、シナリオ設計、測定結果と読み方／検索・選択・ルーティングの挙動を変えるときに、比較の基準として読む。数値は隣の `benchmarks/results/*.json` の同一実行から取る。
- `CONTRIBUTING.md`／公開向けの開発環境構築、CI の再現、リリース手順／外部コントリビューターに見せる手順を確認・修正するとき。
- `SECURITY.md`／脆弱性報告の窓口とスコープ／セキュリティ報告の扱いを確認するとき。
- `CHANGELOG.md`／リリースごとの変更履歴（Keep a Changelog 形式）／利用者に見える変更の記録先。過去のパスを含むので、現在のリポジトリ構成の根拠には使わない。
- `.github/BRANCH_PROTECTION.md`／`main` の保護設定と必須 CI チェックの記録／マージ条件や CI ゲートを確認・変更するときに参照する。
- `.github/PULL_REQUEST_TEMPLATE.md`／PR 本文の型／PR を作るときに埋める。
- `要件定義書１.md`／初期の要件定義／設計の経緯を確認するとき。実装済みの項目は `CHANGELOG.md` で確認する。
- `.claude/RESUME.md`／Claude Code のセッション再開用チェックポイント／手で編集せず、内容を作業の根拠にしない。

設計判断（ADR）は `docs/decisions/README.md` が索引である。判断を変更・追加するときは既存 ADR を確認し、理由と影響を更新・記録する。次の対象を変更するときは、先に該当する ADR を読む。

- `docs/decisions/0008-timeout-outcome-is-uncertain.md`／timeout 後の不明な副作用と実行方式の判断／期限切れ処理・回復動作を変更するとき。
- `docs/decisions/0009-task-budget-reservations.md`／タスク予算の単位・予約・精算と再開時の不変条件／予算処理を変更するとき。
- `docs/decisions/0010-execution-snapshot.md`／選択済み Resource と再開時の fingerprint 検証／task resume の実行契約を変更するとき。
- `docs/decisions/0011-agent-execution-backends-and-structured-tasks.md`／Agent backend と dependency-scoped child Kernel の判断／Agent 実行契約を変更するとき。
- `docs/decisions/0012-multi-intent-retrieval-and-coverage-selection.md`／クエリ分解検索とファセット被覆による集合選択の判断と ToolRet での根拠／`DecomposedRetriever`・`CoverageSetSelector` や集合サイズの決め方を変更するとき。
- `docs/decisions/0014-gate-aware-selection.md`／ゲートが必ず拒否する候補を Selector が選ばず escalate の理由にもしない判断（opt-in）と、既定化を見送った根拠／`SelectionContext.policy`、`static_denials`、`Kernel(gate_aware_selection)` を変更するとき。
- `docs/decisions/0015-execution-right-and-call-journal.md`／タスクの実行権（排他）、呼び出しジャーナル、キャンセル後の終端状態、予算予約の原子性の判断／`StateStore.execution`、`call` event、`closed_calls`、`Kernel._transition` を変更するとき。
- `docs/decisions/0016-mcp-gateway-outside-the-kernel.md`／MCP ゲートウェイ（`MCPGatewayServer`、`marmo mcp-serve`）が Kernel の外で通すゲートと、承認が要る操作を拒否する判断／`mcp_server.py`、または Kernel の候補プール・制約適用・Tool 実行の手順を変更するとき。

公開文書には翻訳版がある。手順、サポート範囲、評価上の主張を変更する場合は、同じ PR で両版を更新する。英語版は `ARCHITECTURE.en.md`、`benchmarks/README.en.md`、`docs/decisions/README.en.md` と同ディレクトリの英語版 ADR、`docs/local-resource-packages.en.md`。日本語版は `docs/connectors.ja.md`、`docs/threat-model.ja.md`、`CONTRIBUTING.ja.md`、`SECURITY.ja.md`。

ドキュメントを追加・削除したら、同じコミットでこの一覧も更新する。文書内のパス参照が存在するかは `python3 scripts/check_doc_paths.py` が CI で検証する。

## ブランチ・コミット・PR

- ブランチ名は `<type>/<topic>`。これまでに使われている type は `fix`、`docs`、`chore`、`ci`、`feat`、`research`。
- コミットの件名は既存履歴に合わせて `<type>: <English summary>` とする（type は `feat` / `fix` / `docs` / `chore` / `ci` / `test` / `refactor`。Dependabot は `ci` を使う）。本文は日本語でも英語でもよい。挙動が変わる修正は、本文に原因・実測値・トレードオフを書く（`git log` の `fix:` コミットが手本）。
- 1 つの PR に種類の異なる変更（バグ修正とリファクタリング、機能追加と無関係な整形など）が含まれる場合は、種類ごとに別コミットに分ける。
- PR のタイトルと本文は日本語と英語の両方を含める（PR titles and descriptions must include both Japanese and English）。タイトルは `<type>: <English summary> / <日本語要約>`。
- PR 本文は `.github/PULL_REQUEST_TEMPLATE.md` に従い、変更内容、関連 issue（あれば）、テスト（実行したコマンドと結果）、判断が要るところ（既定値・終了コード・スコアの変化など利用者に見える差分）を書く。
- 利用者に見える変更は `CHANGELOG.md` の `## [Unreleased]` に同じ PR で英語と日本語の両方を追記する。バージョン番号を上げるのはメンテナの判断であり、リリースコミットは別に切る（`CONTRIBUTING.md` の Releasing）。
- CI ワークフローの `concurrency` は同じ ref の実行中ジョブを打ち切る。`main` に連続してマージすると中間コミットの CI が完了しないことがあるので、リリースタグを打つ前に `main` の最新コミットの CI が緑であることを確認する。

## 進め方

- 作業開始前に現在のブランチと未コミットの変更を確認する。
- 「守る境界」で合意が要るもの以外は、自分で判断して進める。何をどう判断したかは報告に書く。依頼の外で見つけた改善は、変更に混ぜずに提案として報告する。
- 仕様は実装本体とテストから読み取る。コメント、docstring、関数名は実装と食い違っていることがあるので根拠にせず、触った範囲で食い違いを見つけたら同じ変更で直す。
- 根本原因を直す。回避策（待ち時間の追加、例外の握りつぶし、`# noqa`、`# type: ignore`）と理由コメントで済ませない。抑制が設計上必要な場合は、規則コードと理由を添える。
- 変更は依頼を満たす最小の形にし、未使用のヘルパー、過剰な抽象化、コメントアウトした残骸を残さない。
- 同じ種類のミスが再発したら、この文書に規則を足す前に、lint・型・テスト・`scripts/` の検査にできないかを先に検討する。検査にした規則は、本文を検査への 1 行参照に縮める。
- テスト失敗やレビュー指摘への修正が同じ方針で続けて失敗するなら、回数を重ねる前に原因の見立てと方針を見直す。修正の試行は 5 回を上限とし、超えたら自力で続けず、何が未解決でどこで詰まっているかを添えてユーザーに報告する。
- ユーザーへの説明や、作業・編集途中の経過報告はすべて日本語で表示する。

## テストと検証

- 全テストは十数秒で終わる。修正中は変更箇所に対応するテストモジュールだけを回してよいが、PR を作る前には CI と同じコマンドで全体を通す：

  ```bash
  python -W error::ResourceWarning -m unittest discover -s tests
  ruff check marmo_core tests scripts tools
  mypy marmo_core
  python scripts/release_check.py
  python scripts/check_doc_paths.py
  python scripts/check_env_documentation.py
  check-manifest
  ```

- `-W error::ResourceWarning` は省略しない。CI がこの形で走るため、閉じ忘れたファイルやソケットはアサーションが通っても落ちる。
- 手元の Python が `requires-python` の下限（現在 3.11）より新しい場合は、下限のインタープリタでも全テストを回す（`docs/knowledge/development_conventions.md` の「コマンド」）。無ければ PR 本文にその旨を書き、CI の下限のジョブを確認する。
- 修正には回帰テストを付け、「修正を戻すとそのテストが落ちる」ことを確認する。モック LLM のテストだけでは実プロバイダとの不整合は検出できない（`docs/knowledge/lessons_from_history.md`）。
- 追跡ファイルを追加したら `check-manifest` を回す。sdist に入れるなら `MANIFEST.in`、リポジトリ専用なら `pyproject.toml` の `[tool.check-manifest] ignore` に追加する。
- 実行時に読まれる環境変数の一覧は `.env.example` が正本で、`python3 scripts/check_env_documentation.py` がコードの読み取りと記載の同期を検証する。環境変数を追加・削除したら同じ変更で `.env.example` も更新する。現在あるのは LLM プロバイダーの API キー（`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`）、モデル設定（`OPENAI_MODEL`、`ANTHROPIC_MODEL`、`ANTHROPIC_MAX_TOKENS`、`OPENAI_EMBEDDING_MODEL` など）、通知 webhook（`MARMO_NOTIFICATION_<DESTINATION>_URL`）である。
- テストを実行できない場合は、その理由を最終報告に記載する。

## レビュー

コードを変更する PR は、作る前にレビュー用サブエージェント（指定は `docs/knowledge/development_conventions.md` の「サブエージェントの指定」）のレビューを受ける。

- 渡すのはスコープ・差分・チェックリスト（要件を満たす／スコープ外の変更が無い／不要なコードが無い／テストが通る／禁止事項に触れない）だけにする。実装担当の意図や経緯を渡すと、レビューがその説明に引きずられるので渡さない。
- 指摘は検証してから反映する。指摘に反論がある場合は握りつぶさずユーザーに上げる。
- ドキュメントだけの変更はこのレビューを省略でき、省略した場合は PR 本文にその旨を書く。

## AI の出力・ルーティング品質に関わる変更

次の変更は、モデルの応答や順位という、単体テストが検証していないものを変える。単体テストが通るだけでは完了にせず、変更前後を同じ入力で比べた結果を PR 本文に書く。確認の手順と限界は `docs/knowledge/development_conventions.md` の「AI 出力の品質確認」にある。

- **プロンプト文言・ツール定義・会話の組み立て・プロバイダのリクエスト形**（`kernel.py`、`compiler.py`、`planner.py`、`llm_routing.py`、`providers.py`）: 固定したプロバイダ応答によるテスト（`tests/test_provider_compat.py` の transport 差し替え方式）で形式とエラー処理を確認し、可能なら実モデル（OpenAI 互換または Anthropic）で変更前後を実行する。実モデルの応答は再現しないので、CI の合否条件にはしない。
- **検索・選択・ルーティングのスコアや既定値**（`retriever.py`、`semantic.py`、`selector.py`、`graph_routing.py`、`hierarchy.py`、`rerank.py`、`adaptive.py`）: `benchmarks/` の該当スイートを変更前後で実行し、指標を PR 本文に並べる。第1層の関連度成分を変える場合は、第2層（集合選択）の Coverage と abstain/escalate 精度まで確認する（`docs/decisions/0003-absolute-relevance-and-bm25f.md`）。
- スコアの尺度を変えたら、ベンチマークスクリプトの既定しきい値と `benchmarks/README.md` の数値を同じ PR で更新する。

## サブエージェントと git worktree

サブエージェントと git worktree は別の判断軸である。「作業を独立分割できるか」でサブエージェントを、「作業ツリーを共有すると壊れるか」で worktree を判断する。具体的な判断基準と運用手順は `docs/knowledge/parallel_work.md` にある。

- 作業ツリーにユーザーの未コミット変更があるときは、worktree で作業する。数ファイル規模の変更で作業ツリーがきれいなら、worktree は要らない。
- 同時に走る作業が同じファイルを編集する予定なら、worktree を増やしても解決しないので片方を待たせる。1 worktree = 1 ブランチ = 1 PR。
- 最終判定はユーザーで、エージェント間の判断の不一致はユーザーに上げる。

## 研究用変更

新しい Router、Retriever、Selector などを試すときは、最新の `main` から `research/<method-name>` ブランチを切る。実装の形は自由に試してよいが、既存の拡張ポイント（`ARCHITECTURE.md` の「拡張ポイント」）に差し込む形を優先し、unit test を付ける。評価は、テストが通った commit の SHA を `Object-Routing-Research` から固定して行う。ベンチマーク結果には `benchmarks/_provenance.py` が commit SHA を記録するので、結果と実装の対応を後から曖昧にしない。

`main` へ入れる条件：

- 実験上の有効性または必要性が確認されている。
- unit test がある。
- 既存 API を不必要に壊さない（`docs/knowledge/contracts-and-compatibility.md`）。
- 一般利用できる実装になっている。実行時依存を不必要に増やさない（増やす場合はユーザーの確認を取っている）。
- 必要なドキュメント（`CHANGELOG.md`、該当する docs、`ARCHITECTURE.md`）が更新されている。
