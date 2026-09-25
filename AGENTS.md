# Marmo-Core Agent Rules

Marmo-Core は、Object Routing を実装する公開 Python ライブラリである。
このファイルは、このリポジトリで作業するエージェント（と人間）の規約をまとめる。

## 基本方針

- このリポジトリを実装コードの唯一の正とする。
- `main` は安定版として扱う。PyPI に公開される。
- 研究中の新手法は `research/<method-name>` ブランチで実装する。
- `Object-Routing-Research` へ Marmo-Core 本体をコピーしない。評価はそちらから commit SHA を固定して行う。

## ドキュメントの参照先

各行は「パス／内容の区分／いつ参照するか、または何に使わないか」の型で書く。

- `README.md`／公開向けの概要・インストール・Quickstart・CLI と `.env` の使い方／利用者視点の説明を確認・修正するとき。内部設計の正本としては扱わず、実装との差分が見つかった場合は公開向け説明として修正する。
- `ARCHITECTURE.md`／レイヤー構成、`Kernel.run_goal` と CLI のリクエスト経路、契約と境界、拡張ポイントをまとめた内部設計の正本／複数モジュールにまたがる変更では最初に必要な章だけ読む。
- `docs/knowledge/development_conventions.md`／プロジェクト構成、ビルド・テストコマンド、実装規約、命名、責務分割、テスト方針、サブエージェントの指定、AI 出力の品質確認／コードを変更する作業では着手前に必ず読む。
- `docs/knowledge/README.md`／再利用可能な知見の索引／何か調べる前に該当する知見があるか確認する。作業ログや一時的な状態は追加しない。
- `docs/knowledge/debugging.md`／実モデル・検索・CLI・パッケージングの不具合の切り分け手順／動作がおかしいときに、コードを読み始める前に読む。
- `docs/knowledge/contracts-and-compatibility.md`／公開 API、リソース定義、状態ファイル、監査ログ、CLI 終了コードの互換性契約と変更手順／これらの表面に触る変更の前に読む。
- `docs/knowledge/parallel_work.md`／git worktree で作業を分けた後の運用手順／並行作業をするときに読む。
- `docs/knowledge/lessons_from_history.md`／git 履歴と PR から抽出した過去の失敗と教訓／同じ轍を踏まないために、該当領域を触る前に読む。
- `docs/decisions/README.md`／重要な技術判断（ADR）の索引／判断を変更・追加するときは既存 ADR を確認し、理由と影響を更新・記録する。
- `docs/decisions/0009-task-budget-reservations.md`／タスク予算の単位・予約・精算と再開時の不変条件／予算処理を変更するとき。
- `docs/decisions/0010-execution-snapshot.md`／選択済み Resource と再開時の fingerprint 検証／task resume の実行契約を変更するとき。
- `docs/decisions/0011-agent-execution-backends-and-structured-tasks.md`／Agent backend と dependency-scoped child Kernel の判断／Agent 実行契約を変更するとき。
- `docs/decisions/0008-timeout-outcome-is-uncertain.md`／timeout 後の不明な副作用と実行方式の判断／期限切れ処理・回復動作を変更するとき。
- `docs/threat-model.md`／信頼境界・想定脅威・リリース前レビューの記録／権限、副作用、ポリシー、シークレット、HITL に触る変更で読み、境界を動かしたら更新する。
- `docs/connectors.md`、`docs/local-resource-packages.md`／利用者向けマニュアル／実装の責務や内部挙動を確認する資料としては使わない。
- `benchmarks/README.md`／ベンチマークの実行方法、シナリオ設計、測定結果と読み方／検索・選択・ルーティングの挙動を変えるときに、比較の基準として読む。数値は隣の `benchmarks/results/*.json` の同一実行から取る。
- `CONTRIBUTING.md`／公開向けの開発環境構築、CI の再現、リリース手順／外部コントリビューターに見せる手順を確認・修正するとき。
- `SECURITY.md`／脆弱性報告の窓口とスコープ／セキュリティ報告の扱いを確認するとき。
- `CHANGELOG.md`／リリースごとの変更履歴（Keep a Changelog 形式）／利用者に見える変更は `## [Unreleased]` に追記する。過去のパスを含むので、現在のリポジトリ構成の根拠には使わない。
- `.github/BRANCH_PROTECTION.md`／`main` の保護設定と必須 CI チェックの記録／マージ条件や CI ゲートを確認・変更するときに参照する。
- `.github/PULL_REQUEST_TEMPLATE.md`／PR 本文の型／PR を作るときに埋める。
- `要件定義書１.md`、`改善策.md`／初期の要件定義と、2026-09 時点の改善提案メモ／背景を知るための資料であり、現在の実装の説明ではないので、実装判断の根拠として引用しない。実装済みの項目は `CHANGELOG.md` で確認する。
- `.claude/RESUME.md`／Claude Code のセッション再開用チェックポイント／手で編集せず、内容を作業の根拠にしない。

ドキュメントを追加・削除したら、同じコミットでこの一覧も更新する。文書内のパス参照が存在するかは `python3 scripts/check_doc_paths.py` が CI で検証する。

## ブランチ・コミット・PR

- `main` へ直接 push しない。すべての変更は作業ブランチにコミットし、PR で `main` に取り込む。
- ブランチ名は `<type>/<topic>` とする。これまでに使われている type は `fix`、`docs`、`chore`、`ci`、`feat`、`research`。研究手法は必ず `research/<method-name>`。
- コミットの件名は既存履歴に合わせて `<type>: <English summary>` とする（type は `feat` / `fix` / `docs` / `chore` / `ci` / `test` / `refactor`。Dependabot は `ci` を使う）。本文は日本語でも英語でもよい。挙動が変わる修正は、本文に原因・実測値・トレードオフを書く（`git log` の `fix:` コミットが手本）。
- 1 つの PR に種類の異なる変更（バグ修正とリファクタリング、機能追加と無関係な整形など）が含まれる場合は、種類ごとに別コミットに分ける。
- PR のタイトルと本文は日本語と英語の両方を含める（PR titles and descriptions must include both Japanese and English）。タイトルは `<type>: <English summary> / <日本語要約>`。
- PR 本文は `.github/PULL_REQUEST_TEMPLATE.md` に従い、変更内容、関連 issue（あれば）、テスト（実行したコマンドと結果）、判断が要るところ（既定値・終了コード・スコアの変化など利用者に見える差分）を書く。
- 利用者に見える変更は `CHANGELOG.md` の `## [Unreleased]` に同じ PR で追記する。バージョン番号を上げるのはメンテナの判断であり、リリースコミットは別に切る（`CONTRIBUTING.md` の Releasing）。
- エージェントは、ユーザーから明示的な指示がない限り PR をマージしない。

## エージェントの作業ルール

- 作業開始前に現在のブランチと未コミットの変更を確認する。`benchmarks/results/` に未追跡の結果ファイルがあることが多い。これは他の作業の成果物なので、触らず、自分のコミットにも含めない。
- ユーザーまたは他のエージェントによる既存の変更を、明示的な許可なく上書き、破棄、巻き戻ししない。
- 要件が曖昧なまま実装コードを書かない。着手前にスコープとスコープ外を合意し、合意していない変更は加えない。未使用のヘルパー、過剰な抽象化、コメントアウトした残骸などの不要なコードも生成しない。
- コメント、docstring、関数名を仕様の根拠にせず、実装本体とテストを読んで判断する。触った範囲で実装と食い違うコメントや名前を見つけたら、同じ変更で直す。
- テスト失敗やレビュー指摘に対する自動修正のループは 5 回を上限とする。超えたら自力で続けず、何が未解決でどこで詰まっているかを添えてユーザーに報告する。
- 実装したエージェントは自分で完了判定をしない。コードを変更する PR は、作る前にレビュー用サブエージェント（指定は `docs/knowledge/development_conventions.md` の「サブエージェントの指定」）へスコープ・差分・チェックリスト（要件を満たす／スコープ外の変更が無い／不要なコードが無い／テストが通る／禁止事項に触れない）だけを渡してレビューさせ、実装担当の意図や経緯の説明は渡さない。ドキュメントだけの変更はこのレビューを省略でき、省略した場合は PR 本文にその旨を書く。指摘は検証してから反映する。指摘に反論がある場合は握りつぶさずユーザーに上げる。
- ユーザーへの説明や、作業・編集途中の経過報告はすべて日本語で表示する。

## テストと検証

- 全テストは約 500 件で 10 秒強で終わる。修正中は変更箇所に対応するテストモジュールだけを回してよいが、PR を作る前には必ず CI と同じコマンドで全体を通す：

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
- 修正には回帰テストを付け、「修正を戻すとそのテストが落ちる」ことを確認する。モック LLM のテストだけでは実プロバイダとの不整合は検出できない（`docs/knowledge/lessons_from_history.md`）。
- 追跡ファイルを追加したら `check-manifest` を回す。sdist に入れるなら `MANIFEST.in`、リポジトリ専用なら `pyproject.toml` の `[tool.check-manifest] ignore` に追加する。
- テストを実行できない場合は、その理由を最終報告に記載する。

## AI の出力・ルーティング品質に関わる変更

次の変更は、単体テストが通るだけでは完了にしない。

- **プロンプト文言・ツール定義・会話の組み立て・プロバイダのリクエスト形**（`kernel.py`、`compiler.py`、`planner.py`、`llm_routing.py`、`providers.py`）: 固定したプロバイダ応答によるテスト（`tests/test_provider_compat.py` の transport 差し替え方式）で形式とエラー処理を確認し、可能なら実モデル（OpenAI 互換または Anthropic）で変更前後を同じ入力で実行して結果を PR 本文に書く。実モデルの応答は再現しないので、CI の合否条件にはしない。
- **検索・選択・ルーティングのスコアや既定値**（`retriever.py`、`semantic.py`、`selector.py`、`graph_routing.py`、`hierarchy.py`、`rerank.py`、`adaptive.py`）: `benchmarks/` の該当スイートを変更前後で実行し、指標（hit@k、MRR、recall@k、Set F1、abstain/escalate 精度、レイテンシ）を PR 本文に並べる。第1層の関連度成分を変える場合は、第2層（集合選択）の Coverage と abstain/escalate 精度まで確認する（`docs/decisions/0003-absolute-relevance-and-bm25f.md`）。
- スコアの尺度を変えたら、ベンチマークスクリプトの既定しきい値と `benchmarks/README.md` の数値を同じ PR で更新する。

手順と限界は `docs/knowledge/development_conventions.md` の「AI 出力の品質確認」に従う。

## サブエージェントと git worktree

サブエージェントと git worktree は別の判断軸である。「作業を独立分割できるか」でサブエージェントを、「作業ツリーを共有すると壊れるか」で worktree を判断する。

- サブエージェントを使う: 読み取りのみの調査・レビュー、または担当ファイルを重複なく分割できる編集。調査・実装・レビューを分けるときは役割ごとに別の担当にし、各担当にはその役割に必要な情報だけを渡し、同じファイルを同時に編集させない。複数の担当に分けるときは、着手前に「誰の成果物を誰にどの形式で渡すか」「何が揃ったら次を始めてよいか」「最終判定は誰か」を決めて依頼文に書く。最終判定はユーザーで、エージェント間の判断の不一致はユーザーに上げる。
- worktree を使う（いずれか該当時）: 並列作業が同じ生成物（`CHANGELOG.md` の Unreleased、`marmo_core/__init__.py` の `__all__`、`benchmarks/results/*.json`、`tests/fixtures/compat/`）に触る／別 PR に分けるべき変更を同時に進める／破棄する可能性のある大規模リファクタ／作業ツリーにユーザーの未コミット変更がある。
- worktree を使わない: 数ファイル規模の変更。
- 並行数の上限は「担当ファイルが重複しないこと」で決める。同時に走る作業が同じファイルを編集する予定なら、worktree を増やしても解決しないので片方を待たせる。1 worktree = 1 ブランチ = 1 PR。運用手順は `docs/knowledge/parallel_work.md` に従う。

## 研究用変更

新しい Router、Retriever、Selector などを試す場合：

1. `main` を最新化し、`research/<method-name>` ブランチを作る。
2. 実装する。既存の拡張ポイント（`ARCHITECTURE.md` の「拡張ポイント」）に差し込む形を優先し、`Kernel` の既定挙動は変えない。
3. unit test を追加する。
4. テストを実行する。
5. commit SHA を取得する。
6. `Object-Routing-Research` からその commit を使用して評価する。ベンチマーク結果には `benchmarks/_provenance.py` が commit SHA を記録する。

実験で有効性を確認できるまでは、原則として `main` にマージしない。

## main へ入れる条件

- 実験上の有効性または必要性が確認されている。
- unit test がある。
- 既存 API を不必要に壊さない（`docs/knowledge/contracts-and-compatibility.md`）。
- 一般利用できる実装になっている。実行時依存を不必要に増やさない（増やす場合はユーザーの確認を取っている）。
- 必要なドキュメント（`CHANGELOG.md`、該当する docs、`ARCHITECTURE.md`）が更新されている。

## 依存関係・互換性・凍結物

- 実行時依存は最小限に保つ（現在は `python-dotenv` の 1 つ）。新しい実行時依存を追加する前に、必要性、標準ライブラリや既存の依存で代替したときのコスト、インストールサイズ・推移的依存・ライセンスへの影響をユーザーに示し、確認を取る。確認なしに `pyproject.toml` の `dependencies` を変更しない。ベンチマークや開発だけに要るものは `benchmark` / `dev` extra に置く。追加した場合は理由と影響を PR に書く（`docs/decisions/0007-minimal-runtime-dependencies-with-user-approval.md`）。
- `tests/fixtures/compat/v0.3.0/` は互換性契約の凍結物である。書き換えず、新しい契約を凍結するときは新しいバージョンのディレクトリを追加する。
- `benchmarks/results/*.json` はコミットされた測定結果である。実装を変えずに数値だけを変更しない。再測定したら同じ PR で実装差分と一緒に更新し、`benchmarks/README.md` の数値も揃える。
- CI ワークフローの `concurrency` は同じ ref の実行中ジョブを打ち切る。`main` に連続してマージすると中間コミットの CI が完了しないことがあるので、リリースタグを打つ前に `main` の最新コミットの CI が緑であることを確認する。

## セキュリティと設定

- 実行時に読まれる環境変数の一覧は `.env.example` が正本である。`python3 scripts/check_env_documentation.py` がコードの読み取りと記載の同期を検証する。環境変数を追加・削除したら同じ変更で `.env.example` も更新する。
- 必要な環境変数は LLM プロバイダーの API キー（`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`）、モデル設定（`OPENAI_MODEL`、`ANTHROPIC_MODEL`、`ANTHROPIC_MAX_TOKENS`、`OPENAI_EMBEDDING_MODEL` など）、通知 webhook（`MARMO_NOTIFICATION_<DESTINATION>_URL`）である。シークレットは環境変数または `.env` に保持し、git に含めない。
- `.env` には秘密情報が入るため、その内容を読んだり、ログ・文書・報告へ転記したりしない。環境変数の一覧を確認するときは `.env.example` を読む。
- `resources/skills` はサードパーティのコーパスで、再配布しない。git と sdist の両方から除外されている。
- 権限、副作用分類、ポリシー評価、シークレット処理、HITL ゲートに触る変更は `docs/threat-model.md` に照らしてレビューし、信頼境界を動かしたら同文書を更新する。

## 最重要ルール

研究速度のために公開ライブラリの安定性を壊さない。一方で、研究用ブランチでは新しい手法を積極的に試してよい。
