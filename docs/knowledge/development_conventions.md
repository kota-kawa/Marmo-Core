# 開発規約

コードを変更する前に読む。全体像は `ARCHITECTURE.md`、契約の変更は
`contracts-and-compatibility.md`、過去の失敗は `lessons_from_history.md`。

## プロジェクト構成

- `marmo_core/`: ライブラリ本体。単一パッケージ、サブパッケージは `sample_resources/` のみ。
- `tests/`: `unittest`（pytest は使っていない）。`tests/test_<module>.py` がモジュールに対応する。
  横断的な表面ごとのテストもある（`test_v1.py`、`test_v03.py`、`test_compatibility.py`、
  `test_security_boundaries.py`、`test_provider_compat.py`、`test_release_readiness.py`、
  `test_repo_checks.py`）。
- `benchmarks/`: 実測スイート。`Object-Routing-Research` から実行するのが本筋で、
  ここにはライブラリの主張を検証する最小構成と、コミットされた結果 JSON を置く。
- `scripts/`: CI が呼ぶ検査。`tools/`: 開発者専用ユーティリティ。
- 配布物: sdist と wheel は `MANIFEST.in` と `check-manifest` で内容を管理する。
  Docker イメージは `Dockerfile` が `marmo_core`、`examples`、`resources`、`scripts`、`tests`
  だけをコピーし、コンテナ内でテストを回す。

## コマンド

```bash
python -m pip install -e '.[dev]'                 # 開発環境
python -W error::ResourceWarning -m unittest discover -s tests   # 全テスト（約 10 秒）
python -W error::ResourceWarning -m unittest tests.test_kernel   # モジュール単位
ruff check marmo_core tests scripts tools
mypy marmo_core
python scripts/release_check.py                   # バージョン整合と CHANGELOG
python scripts/check_doc_paths.py                 # 文書内のパス参照
python scripts/check_env_documentation.py         # .env.example と環境変数の読み取り
check-manifest                                    # 追跡ファイルと sdist の一致
python -m build && python -m twine check dist/* && check-wheel-contents dist/*.whl
docker build --tag marmo-core:ci . && docker run --rm marmo-core:ci python -m unittest discover -s tests
marmo validate resources/memory resources/tools resources/agents   # サンプルリソース
```

CI（`.github/workflows/ci.yml`）は Python 3.10〜3.14 でテストを回し、3.14 で静的検査と
リリース検査、Docker ジョブを実行する。PR を作る前にこれらを全部ローカルで通す。

## 実装規約

- **実行時依存を増やさない。** 依存は `python-dotenv` のみ。HTTP は `urllib`、YAML 風の
  フロントマターは自前パーサ、永続化は JSONL と `sqlite3`。外部モデル（fastembed など）は
  `benchmark` extra に隔離し、コアは `EmbeddingProvider` / `CrossEncoderProvider` の
  ABC だけを持つ。
- **`from __future__ import annotations`** を全実装モジュールで使う（`__init__.py` と `_version.py` を除く）。型ヒントは `mypy marmo_core`
  が通る範囲で付ける。`py.typed` を同梱しているので、公開 API の型は利用者に見える。
- **例外は `errors.py` の階層に載せる。** プロバイダ由来は `ProviderError` /
  `ProviderHTTPError`、入力由来は `ToolInputError`。Kernel の実行ループから例外を外に
  出さない（タスクを `failed` で終端し、監査ログを書く）。
- **秘密の扱いは `secrets.py` に集約する。** 伏せ字パターンを他の場所に複製しない。
  エラーメッセージ、ログ、監査レコード、resume ヒントに値を出す経路は
  `redact_credentials` を通す。
- **決定性。** テストとベンチマークは実ネットワークに出ない。プロバイダは `transport`
  を注入でき、ベンチマークの LLM 応答はファイルキャッシュで再現する。
  `HashingEmbeddingProvider` はオフラインの代替であって意味検索ではない。
- **ゲートはバイパス経路を作らない。** activation / execution / output の 3 ゲートと
  `SafetyInspector`、HITL エスカレーションが制御点。候補プールを広げる・スコアを変える
  変更をしても、ゲートを迂回する道を作らない（`docs/threat-model.md`）。
- **無言の成功を作らない。** 一致なし、Tool がモデルに届かない、壊れた JSON、モデル
  呼び出しの失敗は、`detail`、警告、`--strict` の失敗のいずれかで表に出す。
- **設定は `.env` と引数の二段。** 環境変数はコンストラクタで明示引数が無いときだけ
  `environment.py` のヘルパーで読む。新しい変数は `.env.example` に同じ変更で書く。
- **サンプルリソース**は `python:` 参照で標準ライブラリ実装に解決し、実際に必要な権限と
  副作用だけを宣言し、ファイルアクセスはカレントディレクトリ内に閉じる。

## 命名

- モジュールは責務の名詞（`retriever.py`、`selector.py`、`policy.py`）。研究案の記号
  （案A〜案I）はコードに持ち込まず、`benchmarks/README.md` と ADR で対応付ける。
- リソース id は `<kind>.<namespace>.<name>`（`tool.marmo.samples.read-text`）。ドットを
  含むため wire 上では `ToolNameCodec` でエンコードされる。
- 環境変数は `OPENAI_*` / `ANTHROPIC_*` / `BENCHMARK_*` / `MARMO_*` の接頭辞。
- CLI フラグは `--kebab-case`、繰り返し指定する許可リストは単数形（`--allow-side-effect none
  --allow-side-effect read`）。
- テストメソッド名は挙動を文で書く（`test_strict_fails_when_no_callable_reached_the_model`）。

## 責務分割

- 検索（`Retriever`）は候補の **順序と関連度** を決める。選択（`SetSelector`）は
  **制約充足と集合** を決める。実行可否は **ゲート** が決める。層をまたいで判断を持ち込まない
  （例: Retriever に権限フィルタをハードコードすると escalate 能力が壊れる。
  `benchmarks/README.md` の Policy アブレーション）。
- Kernel は束ね役であり、アルゴリズムを持たない。新しい手法は拡張ポイント
  （`ARCHITECTURE.md` 5 章）に差し込む。
- `ExecutionEvaluator` と `CaseBasedRouter` は Kernel の外で合成する。組み込むなら ADR。

## テスト方針

- 修正には回帰テストを付け、修正を戻すとそのテストが落ちることを確認する。
- モックだけで完結する変更でも、プロバイダとの wire 形式に触るなら固定した HTTP 応答
  （`transport` 差し替え）でリクエスト本文とエラー処理を検証する。
- 契約（公開 API、リソース定義、状態ファイル）は `tests/fixtures/compat/` の凍結物で守る。
  凍結物は書き換えず、新バージョンのディレクトリを足す。
- 同梱サンプル、examples、CLI は実際に実行するテストで守る（`test_resource_samples.py`、
  `test_v2_examples.py`、`test_cli_release.py`）。
- 全テストは 10 秒強なので、PR 前は必ず全体を回す。個別実行は開発中の反復用。

## サブエージェントの指定

- **レビュー用サブエージェント**: `Agent` ツールの `general-purpose`（読み取り専用にしたい
  場合は `Explore`）。渡すものは、スコープ（何を変えるべき変更か）、差分（`git diff main...HEAD`
  または PR 番号）、チェックリスト（要件を満たす／スコープ外の変更が無い／不要なコードが無い／
  テストが通る／禁止事項に触れない）。実装担当の意図や経緯は渡さない。
- **調査用サブエージェント**: `Explore`。ファイルの場所と事実の収集に使い、判断はさせない。
- **LLM 代替サブエージェント（AI 出力の品質確認）**: `general-purpose`。変更前後の
  プロンプトやツール定義に同じ入力を与え、出力の差を比較させる。本番モデルの挙動を再現する
  ものではないので、結論ではなく差分の観察として PR に書く。
- 役割ごとに担当を分け、同じファイルを同時に編集させない。最終判定はユーザー。

## AI 出力の品質確認

対象: プロンプト文言（`kernel.py` のシステムプロンプト、`llm_routing.py` の HyDE / 再ランク /
集合選択プロンプト、`planner.py`）、ツール定義の組み立て（`compiler.py`、`providers.py`）、
会話フレームの構築、プロバイダのリクエスト形、検索・選択のスコアと既定値。

手順:

1. **固定応答テスト**: `tests/test_provider_compat.py` の方式で transport を差し替え、
   送信本文（ツール名のエンコード、`max_tokens` の選択、メッセージ順序）と、400 / 401 /
   タイムアウト時の挙動を検証する。これが CI の合否条件。
2. **ベンチマーク前後比較**（検索・選択・ルーティングに触る場合）: `benchmarks/` の該当
   スイートを `main` と作業ブランチで同じ環境・同じ引数で実行し、hit@k / MRR / recall@k /
   Set F1 / abstain・escalate 精度 / レイテンシを表にして PR 本文に書く。結果 JSON を更新
   するなら `benchmarks/README.md` の数値も揃える。関連度の尺度を変えた場合は第2層の
   Coverage まで見る。
3. **実モデル確認**（プロンプトやリクエスト形に触る場合）: OpenAI 互換または Anthropic の
   実モデルで、README に載っているコマンドと `examples/*.py` を変更前後で実行し、
   完走の有無、選ばれたリソース、終了コード、監査ログの kind 列を PR 本文に書く。
   応答は再現しないので CI には入れない。
4. **LLM 代替サブエージェントによる比較**（実モデルが使えない場合の補助）: 同じ入力で
   変更前後のプロンプトを評価させ、差分の観察を PR 本文に書く。

限界: いずれもモデルの確率的な挙動を保証しない。「テストが通った」ではなく「何をどの入力で
確認し、何を確認できていないか」を書く。
