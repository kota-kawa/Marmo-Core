# 実験の進め方（ランブック）

検索・選択・ルーティングの実験を、Claude Code のクラウドセッションとローカル PC のどちらでも
迷わず再開できるようにするための手順。評価設計の約束事は環境によらず共通で、違うのは
LLM の呼び方、計算資源、長時間ジョブの守り方である。

「検証済み」はこの手順で実際に動かした環境、「未検証」は推奨だが手順をまだ通していないもの。
過去の失敗の具体例は `lessons_from_history.md`、各ベンチマークのコマンドと結果の読み方は
`benchmarks/README.md`（英語版 `benchmarks/README.en.md`）にある。

## 1. 共通の手順

### 準備

```bash
python -m pip install -e '.[dev,benchmark,benchmark-toolret]'   # fastembed と pyarrow はベンチマーク専用
python3 benchmarks/run_toolret_benchmark.py --download --retrievers lexical   # ToolRet を取得（約 16MB）
```

- ToolRet などの公開データは `benchmarks/data/`、LLM 応答と埋め込みのキャッシュは `benchmarks/cache/` に置く。
  どちらも git 管理外で、再配布しない。
- 実行時依存（`pyproject.toml` の `dependencies`）は増やさない。実験だけに要るものは `benchmark` extra に置く。

### 段階に分けて実行する

1. **候補の検索**: 埋め込みは初回に全文書を計算し、`benchmarks/cache/embeddings/` に保存する。
2. **LLM の段**（分解、再ランク、集合選択、ラベル付けなど）: 応答はキャッシュに保存する。
   途中で止まっても、同じコマンドを再実行すれば済んだ分は呼ばれない。
3. **採点**: キャッシュを再生するだけでモデルを呼ばない。指標や集計を直したら、採点だけをやり直す。

```bash
python3 benchmarks/run_toolret_llm_stages.py --stage decompose --model haiku --workers 6   # LLM 分解のキャッシュ
python3 benchmarks/run_toolret_benchmark.py --per-subset 60 --retrievers hybrid-0.5,llm:hybrid-0.5
python3 benchmarks/run_forgery_benchmark.py                                  # LLM なし、約 90 秒
```

### 評価設計の約束

- **dev と test を分ける**: ToolRet はクエリ ID の SHA-1 で 50/50 に分ける。しきい値や重みは dev で選び、
  test は報告に一度だけ使う。一度見た test は、手法を直した後の評価に使わない。
- **事前登録**: 主指標と採否の基準を結果を見る前に決めて記録する。満たさなければ、結果が良くても推奨しない。
- **信頼区間**: 差は対応のあるブートストラップ（2,000 回、95%）で示す。区間は主指標と同じ定義で計算する。
  別々の実行どうし（埋め込みモデル違いなど）は `--records` と `benchmarks/compare_toolret_records.py` で対応づける。
- **LLM をアノテータにするとき**: 評価対象の手法とは別のモデルを使い、第 2 のモデルとの一致度（κ）を報告する。
  人のラベルではないことを限界に書く。
- **上限を分けて測る**: 正解を候補に入れた条件（オラクル候補）も測り、検索の取りこぼしと選択の誤りを分ける。
- **出所（provenance）**: 結果 JSON には `benchmarks/_provenance.py` が commit SHA を刻む。コードをコミットしてから
  測り、コミットに無い作業ツリーや別ブランチで測った結果を `main` に入れない。
- **文書に書く数値**: コミットした結果 JSON から辿れる値だけを書く。日本語版と英語版の README を同じ PR で揃える。

### 長時間ジョブを守る

- ジョブは `nohup ... > log 2>&1 &` で裏で走らせ、ログは消えない場所に置く。
- LLM ジョブはクエリ単位で手法を交互に並べる。途中で止まっても、手法間で件数が揃う。
- CPU の長い計算（44k 件の埋め込みなど）は途中保存する（`CachedEmbeddingProvider` は 2,000 件ごと）。
- モデルの安全機構による拒否は再試行しても同じなので、手法の出力（棄権など）として記録する。

## 2. Claude Code のクラウドセッション（検証済み）

| 項目 | 実測・挙動 |
|---|---|
| 計算資源 | CPU 4 コア、RAM 15GB、GPU なし |
| LLM | `claude -p`（`benchmarks/_claude_cli.py` の `ClaudeCLIProvider`）。API キー不要 |
| 並列度 | 6〜8 並列で約 1.4 呼び出し/秒（Sonnet。Haiku も同程度） |
| 使えるモデル | **Haiku 5.5 だけ**（`--model haiku`。2026-11 時点で `claude-haiku-5-5` を指す）。Sonnet は使わない |
| 利用上限 | 5 時間ごとの上限と週の上限がある。`You've hit your 5-hour limit` などで失敗する。Sonnet は約 1,100 回で 5 時間の上限に達した（2026-11） |
| 外部ネットワーク | プロキシ経由で HuggingFace（データとモデル）と PyPI に届く |
| 持続性 | ワーカーが再起動すると、裏で動くプロセスが止まる。リポジトリ内のファイル（`benchmarks/cache/` を含む）と scratchpad は残る |

- **LLM の呼び方**: 評価対象と同じライブラリ部品（`LLMQueryDecomposer`、`LLMSetSelector` など）を、
  `ClaudeCLIProvider` で動かす。
- **モデルは Haiku 5.5 だけを使う**: クラウドセッションでは、ベンチマークの LLM 呼び出しもサブエージェントも
  Haiku 5.5 にする。Sonnet は利用上限にすぐ達し、測定を 1 回のセッションで終えられないためである。
  - スクリプトと `ClaudeCLIProvider` の既定は `sonnet` なので、`--model haiku` を必ず付ける
    （`claude-haiku-5-5` のような正式 ID も使える）。`ClaudeCLIProvider` が実行前に拒否するのは
    Sonnet と Haiku 以外だけで、Sonnet の指定は止めない。
  - 1 つの結果ファイルの中でモデルを混ぜない。応答のキャッシュはモデルを区別しないので、別のモデルで
    作ったキャッシュが残っていたら退避してから作り直す。
  - アノテータと評価対象は別のモデルにする約束（上の「評価設計の約束」）は変わらない。Haiku 以外の
    モデルが要るラベル付けや比較は、クラウドではなくローカルで行う。
  - この規約より前の測定には Sonnet を使ったものがある。ToolRet-SAE（研究ブランチ）のラベルは Opus で付けた。
- **呼び出し数の見積もり**: 1,689 クエリの分解で約 20 分、ラベル付けで約 30 分（並列 6〜8）だった。
  上限に達したら、リセット時刻の後に同じコマンドを再実行する（キャッシュ済みの分は呼ばれない）。
  優先順位を決め、大きな条件（オラクル候補など）は一部のクエリに絞る。
- **埋め込みの所要時間**（CPU 4 コア、44,453 文書、他の処理と CPU を共有した状態の見積もり）:

  | モデル | 時間 |
  |---|---|
  | MiniLM-L6 | 約 40 分 |
  | Arctic-Embed-S | 約 90 分 |
  | bge-small-en-v1.5 | 約 4 時間 |
  | bge-base-en-v1.5 | 10 時間以上 |

  base 級以上のモデルはこの環境に向かない。
- **ログの置き場所**: scratchpad に置く。`/tmp` の他の場所は再起動で消えたことがある。
  終わったらこまめにコミットして push する。
- **待ち方**: シェルの `sleep` による待機はブロックされる。`run_in_background` で `until` ループを回すか、
  Monitor を使う。前景のコマンドは 10 分で打ち切られる。
- **使えないもの**:
  - Docker デーモンが無い。Docker ジョブの失敗は、`Dockerfile` と `.dockerignore` が作るファイル構成を
    手元に再現してテストする。
  - ベンチマーク extra が入れた numpy の型定義で、システムの mypy が止まる。numpy の無い venv で
    `mypy marmo_core` を回す。
- **GitHub**: issue と PR は MCP の GitHub ツールで扱う。push できるのはセッションで許可されたブランチだけである。

## 3. ローカル PC（未検証の推奨を含む）

| 項目 | クラウドとの違い |
|---|---|
| LLM | Claude Code CLI、Anthropic API、OpenAI 互換 API、AWS Bedrock から選べる。費用は自己負担 |
| 計算資源 | GPU があれば大きな埋め込みモデルを使える。無ければ AWS の GPU インスタンスで埋め込みだけ計算する |
| 持続性 | 再起動で消えないが、長時間ジョブの途中保存とキャッシュの方針は同じ |
| 検査 | Docker イメージを実際にビルドして `docker run` でテストできる |

- **シークレット**: API キーは `.env` か OS の環境変数に置き、git に含めない。使う変数の一覧は `.env.example` にある。
- **Claude Code CLI がある場合**（検証済みの経路と同じ）: ログイン済みなら、クラウドと同じスクリプトがそのまま動く。
  利用上限もクラウドと同じように効く。
- **Anthropic API を使う場合**（未検証）: `AnthropicLLMProvider`（`ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL`、
  `ANTHROPIC_MAX_TOKENS`）。ただし ToolRet の LLM 段のスクリプト（`benchmarks/run_toolret_llm_stages.py`）は、
  今は `ClaudeCLIProvider` を直接使っている。API で回すにはプロバイダを選べるようにする小さな変更が要る。
- **AWS Bedrock を使う場合**（未検証）: `BedrockLLMProvider` は OpenAI 互換の Chat Completions を使う。
  そのため Bedrock 経由では Claude を呼べない（既定は `openai.gpt-oss-120b-1:0`）。
  Claude 以外のモデルを比較対象や第 2 アノテータにするときに向く（同系統モデルの相関を避けられる）。
  設定は `BEDROCK_API_KEY` または `AWS_BEARER_TOKEN_BEDROCK`、`BEDROCK_MODEL`、`BEDROCK_REGION`。
- **埋め込みを GPU で計算する場合**（未検証）:
  - fastembed には GPU 版のパッケージ（`fastembed-gpu`）があり、`benchmark` extra の代わりに入れる。
  - AWS の GPU インスタンスで計算するときは、`benchmarks/cache/embeddings/` の `.npy` と `.keys.json` を
    持ち帰れば、ほかの段は CPU の環境で続けられる。キャッシュのキーは本文の SHA-1 なので、文書の変換が同じなら再利用できる。
- **費用**: LLM API と GPU インスタンスは従量課金である。分解・ラベル付けの呼び出し数（クエリ数 × 段数）を先に見積もり、
  dev の一部で試してから全件に広げる。

## 4. 使い分け

| やりたいこと | 向いている環境 |
|---|---|
| Haiku で足りる LLM 段（分解、再ランク、集合選択、判定） | クラウド（API キー不要、Haiku 5.5 だけ）。上限に達したらローカルの CLI か API |
| Sonnet など Haiku 以外の Claude を使う測定、評価対象と別のモデルによるラベル付け | ローカル（Claude Code CLI か API） |
| Claude 以外のモデルとの比較、第 2 アノテータ | ローカル（OpenAI 互換 API か Bedrock） |
| base 級以上の埋め込みモデル | ローカルの GPU か AWS の GPU インスタンス |
| Docker イメージでの確認 | ローカル |
| 字句検索、LLM なしのベンチマーク | どちらでも |
