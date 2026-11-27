# ルーティングベンチマーク

[English](README.en.md)

Marmo-Core の中核主張 —「大量のリソースから、必要なものだけを速く・安全に・コンテキスト汚染なしに選べる」— を実測で検証するスイートです。約 1,000 件のサードパーティ Skill コーパス(`resources/skills`)に対して、ラベル付きシナリオ 120 件を実行します。

## コーパスの入手について

`run_benchmark.py` が既定で使う `resources/skills`(約 260MB)は**外部リポジトリからコピーしたサードパーティ資産で、git にも PyPI の配布物(sdist / wheel)にも含まれていません**。再配布ライセンスの整理が済んでいないためです(下の「注意」参照)。

コーパスが無い環境で `run_benchmark.py` を実行すると、トレースバックではなく次の案内付きエラーで停止します。

- `--resources PATH` で手持ちのリソースディレクトリを指定する
- `tools/collect_skills.py` でコーパスを再収集する(GitHub トークンが必要)
- コーパス同梱の他のベンチマーク(`run_set_benchmark.py` / `run_scale_benchmark.py` / `run_adaptive_benchmark.py`)を使う。これらは `benchmarks/corpus/set_corpus.json` と生成スクリプトだけで完結するため、チェックアウトまたは展開した sdist のルートからそのまま実行できます

## 実行方法

```bash
python3 benchmarks/run_benchmark.py                          # BM25(ゼロ依存)
python3 benchmarks/run_benchmark.py --retriever hybrid-hash  # BM25 + ハッシュ埋め込み
python3 benchmarks/run_benchmark.py --retriever hybrid-model --semantic-weight 0.9
                                                             # BM25 ∪ 実埋め込み(要 pip install '.[benchmark]')
python3 benchmarks/run_benchmark.py --query-transform hyde   # HyDE クエリ変換(案A 派生。要 OPENAI_API_KEY)
python3 benchmarks/run_benchmark.py --llm-rerank             # LLM 再ランク(案C 最小。要 OPENAI_API_KEY)
```

結果は `benchmarks/results/` に JSON で保存されます。`hybrid-model` の `--semantic-weight 0.9` は 0.3〜0.95 のスイープで最良だった設定です(下表)。HyDE / 再ランクの LLM 応答は初回実行時に `benchmarks/cache/` へ保存され（このディレクトリは git 管理外）、同じ環境での再実行はキャッシュ命中により LLM を呼ばず決定的に再現されます。

## シナリオ設計

シナリオは 120 件で、3 つの言い回しスタイルに分類されています。

| スタイル | 件数 | 内容 |
|---------|------|------|
| `direct` | 52 | リソース記述と語彙が重なるタスク文(素直な検索) |
| `paraphrase` | 35 | 同義語への言い換えで語彙の重なりを意図的に消したタスク文 |
| `abstract` | 33 | ドメイン語彙を使わずゴールだけを述べたタスク文 |

コーパスには重複能力(TDD スキルが 6 件、セキュリティ監査が複数件など)があるため、`expected` は**許容できるリソース ID 部分文字列のリスト**で、いずれかが一致すればヒットです。これにより旧版(単一正解・20 件)にあった「同カテゴリの競合が 1 位になっただけの偽ミス」を排除しています。

## 最新結果(120 シナリオ / 1,000 リソース)

| 指標 | BM25(lexical) | hybrid-hash | hybrid-model(bge-small, w=0.9) |
|------|------|------|------|
| hit@1 / hit@5 / MRR(全体) | 65% / 77% / 0.694 | 62% / 72% / 0.659 | **77% / 87% / 0.810** |
| hit@1 — direct | 85% | 85% | **92%** |
| hit@1 — paraphrase | 46% | 43% | **57%** |
| hit@1 — abstract | 55% | 46% | **73%** |
| recall@20 / recall@50(全体) | 88% / 91% | 86% / 86% | **97% / 98%** |
| recall@50 — direct / paraphrase / abstract | 98% / 83% / 88% | 98% / 74% / 79% | **100% / 94% / 100%** |
| ウォーム検索レイテンシ(平均 / p95) | **7.0ms / 15.2ms** | 54.2ms / 62.1ms | 59.2ms / 88.0ms |
| コンテキストトークン | 全カタログ約 221,000 → top-5 約 1,400(**99.4% 削減**) | 同等 | 同等 |

`hybrid-model` は `BAAI/bge-small-en-v1.5`(fastembed / ONNX / CPU)。初回のインデックス構築(全 1,000 件の埋め込み計算)は本測定環境で約 140 秒で、レジストリの**コンテンツ**リビジョン単位でキャッシュされます(実績統計の書き戻しでは無効化されません)。レイテンシ欄は `benchmarks/results/*.json` に記録された同一実行の値で、測定機の負荷で 2 倍程度は動きます(精度指標は決定的で再現します)。

### スコアリング変更(絶対関連度 + フィールド重み付け)の前後比較

関連度成分を「その検索での最高点で割る相対正規化」から「クエリ語をすべて 1 回ずつ含む文書を基準にした絶対値」へ変え、SKILL.md 本文を宣言メタデータより低い重みで索引する(BM25F、`BODY_FIELD_WEIGHT=0.25`)変更の、同一環境での実測です。

| 指標 | 変更前 | 変更後 |
|------|------|------|
| BM25 hit@1 / hit@5 / MRR | 61.7% / 75.8% / 0.668 | **65.0% / 76.7% / 0.694** |
| BM25 hit@1 — direct / paraphrase / abstract | 90% / 31% / 48% | 85% / **46%** / **55%** |
| BM25 recall@20 / recall@50 | 84% / 90% | **88% / 91%** |
| hybrid-model(bge-small) w=0.5(既定値) | 67% / 78% / 0.713 | **70% / 81% / 0.745** |
| hybrid-model(bge-small) w=0.9(調整済) | 78% / 87% / 0.811 | 77% / 87% / 0.810 |
| hybrid(実 OpenAI 埋め込み) w=0.5 | 68.3% / 81.7% / 0.740 | **72.5% / 88.3% / 0.789** |
| hybrid(実 OpenAI 埋め込み) w=0.9 | 75.0% / 92.5% / 0.825 | 74.2% / 92.5% / **0.829** |

- **絶対化の影響はクランプ由来の 2 件のみ**です。クエリごとの定数で割るだけなので本来は順位が変わりませんが、基準文書を上回った文書は 1.0 で頭打ちになり同点になります。同じコードで割る対象だけを旧方式に戻して測ると hit@5・recall@20・recall@50 は完全一致、hit@1 は 66.7% → 65.0%(MRR 0.702 → 0.694)で、120 件中 2 件が 1 位から外れます。上表の改善はフィールド重み付けによるもので、絶対化はその 2 件を代償に「棄権のしきい値が機能する」ことを買っています。
- **direct が 90% → 85% に下がり、paraphrase が 31% → 46%、abstract が 48% → 55% に上がりました**。本文に偶然含まれる語での一致が減り、宣言メタデータでの一致が相対的に強くなった結果です。
- **既定の `semantic_weight=0.5` では実埋め込みでも改善**(hit@1 +3〜4pt、recall@50 +5〜7.5pt)。調整済みの 0.9 では同等(±1 シナリオ)です。旧 README に記載していた `semantic_weight` スイープ(0.9 が最良)は変更前のスコアリングでの測定なので、再スイープが必要です。
- **種別をまたぐ比較が成立するようになりました**: 「read a local text file safely」で、本文 7,551 トークンの XXE 検査スキル(0.790)ではなく `tool.marmo.samples.read-text`(0.567)が 1,030 件中 1 位になります。

## LLM 支援ルーティング(HyDE / LLM 再ランク、gpt-4o-mini)

第1層に小さな LLM 呼び出しを加える 2 方式(15.2 案A 派生 / 案C 最小)を、上記と同一条件で計測しました。

| 指標 | HyDE + BM25 | 再ランク + BM25 | HyDE + hybrid-model | 再ランク + hybrid-model | HyDE + 再ランク + hybrid-model |
|------|------|------|------|------|------|
| hit@1 / hit@5 / MRR | 66% / 83% / 0.729 | 79% / 86% / 0.819 | 87% / 94% / 0.894 | 85% / 92% / 0.879 | **92% / 97% / 0.936** |
| hit@1 — direct | 79% ⚠ | 94% | 92% | 94% | **98%** |
| hit@1 — paraphrase | 46% | 60% | 80% | 80% | **86%** |
| hit@1 — abstract | 67% | 76% | 85% | 76% | **88%** |
| recall@20 / recall@50 | 90% / 93% | 88% / 90% | 98% / 100% | 96% / 99% | **100% / 100%** |

- **HyDE(クエリ変換)**: タスク文を「仮想的なリソース記述」へ 1 回の LLM 呼び出しで書き換えてから検索します。paraphrase / abstract を大きく救う一方、**BM25 単体と組むと direct が 90%→79% に悪化**します(書き換えが元の正確な語彙を薄めるため)。埋め込み検索と併用するとこの悪化はほぼ消えます。
- **LLM 再ランク(案C 最小)**: 候補上位 50 件の軽量メタデータを LLM に見せて並べ替えます。hit@1 を安価に押し上げますが(BM25 単体 61%→79%)、**候補プールに正解がなければ無力で、recall@50 は第1層の値で頭打ち**(BM25 の 90% のまま)。「第1層の recall が後段の上限を決める」という 15 章の層構造の主張の直接的な実証です。
- **フルスタック(HyDE + 再ランク + hybrid-model)が最良**: hit@1 92%、recall@20 100%。第2層(案H 集合選択)には「上位 20 件に正解が必ず入っている」候補プールを渡せる水準です。
- **コストとレイテンシ**: LLM 呼び出しはタスクあたり HyDE 1 回(短文)+ 再ランク 1 回(約 2〜3k トークン)で、gpt-4o-mini なら 120 シナリオ合計でも数十円程度。未キャッシュ時のウォームレイテンシは約 1.8〜2.4 秒/クエリと、非 LLM 構成(4〜63ms)より 2 桁大きい点がトレードオフです。表のレイテンシ詳細は各 JSON を参照してください。

## 結果の読み方

- **スタイル別の分離が案A(ルールベース路線)の実力を正確に示します**: 語彙が重なる direct では hit@1 90% と実用水準ですが、言い換え(29%)・抽象化(48%)で大きく崩れます。これは要件定義書 15 章の案Aの短所(「語彙の一致に依存」)の定量的な裏付けです。
- **hybrid-hash はゼロ依存のオフライン代替であり、真のセマンティック検索ではありません**。paraphrase をわずかに改善(+5pt)する一方 abstract を悪化させ、全体では BM25 と同等です。案Bの本命はモデルベース埋め込み(hybrid-model)です。
- **実埋め込み(hybrid-model)が案Bの主張を実証しました**: hit@1 61%→77%、paraphrase 29%→57%、abstract 48%→70%、recall@50 90%→99%(paraphrase 83%→97%)。前提として候補生成を「BM25 上位のみ」から「**BM25 ∪ 埋め込み近傍の和集合**」へ拡張しています — BM25 候補の再ランクだけでは、語彙が全く重ならない言い換えは候補プールに入れず、recall が BM25 の上限で頭打ちになるためです。
- **hybrid 系のウォームレイテンシ約 60ms** は、クエリごとに全コーパスとのコサイン類似度を純 Python で計算するコストです。1,000 件では許容範囲ですが、10k 件以上では ANN か階層型ルーティング(案I)が前提になります。
- 旧版(単一正解・20 件)の hit@1 70% は、複数正解ラベル化により direct 90% に相当することが判明しました。旧数値との直接比較はできません。
- **レイテンシ**は転置インデックス + BM25 化(v0.3.0)の主目的で、v0.2 の difflib 実装(約 2,460ms)から約 500 倍の改善です。
- **recall@K は第2層(集合選択 / 要件定義書 15 章 案H)への入力品質を測る指標です**: Set Selector は上位 K 件の候補プールから集合を選ぶため、正解が K 件以内に入っていなければどんな Selector でも救えません。BM25 でも recall@50 は 90%(paraphrase でも 83%)あり、「BM25 で 50 件へ縮約 → 制約付き集合最適化」というパイプラインの成立条件を満たしています。ラベルが「許容 ID のいずれか一致」方式のため、recall@K は hit@K と同義です。

## 集合選択ベンチマーク(第2層 / 案H)

`run_set_benchmark.py` は第2層(集合選択)を Set 指標で評価します。コーパスは `generate_set_corpus.py` が生成する **4種混合・制約付きコーパス**(63 リソース: 12 ドメイン × {memory, skill, 主 tool, 代替 tool, agent}。agent→主 tool→skill の依存連鎖、主 tool と代替 tool の競合宣言、権限ゲート付きドメイン、依存欠落 tool を含む)と、ゴールド集合付きシナリオ 28 件(selected 24 / escalate 2 / abstain 2)です。

```bash
python3 benchmarks/generate_set_corpus.py                    # コーパス・シナリオを再生成
python3 benchmarks/run_set_benchmark.py --pool 63            # BM25 検索 + 選択
python3 benchmarks/run_set_benchmark.py --retriever hybrid-model --pool 63
python3 benchmarks/run_set_benchmark.py --retriever hybrid-model --distractors resources/skills --pool 50
python3 benchmarks/run_set_benchmark.py --llm-selector --llm-model gpt-4o   # LLM Set Selector も比較(要 OPENAI_API_KEY)
python3 benchmarks/run_set_benchmark.py --retriever graph-hybrid-model --distractors resources/skills   # 案E グラフ拡張
```

**比較対象**: `topk`(種別ごと Top-1、v1 の RuleBasedSetSelector = 制約推論なしの基準線)、`greedy`(案H ソルバー第1弾 `GreedyConstrainedSetSelector`: 依存閉包単位の効用合計 Σu で貪欲選択、競合・権限・予算制約を充足)、`beam`(案H ソルバー第2弾 `BeamSearchSetSelector`)、`bnb`(案H の厳密解ソルバー `BranchAndBoundSetSelector`: 依存閉包単位の include/exclude を許容上界付き分枝限定法で全探索し、Σu の**厳密最適解**を返す。近似ソルバーとの差 = 近似ギャップの測定用)、`llm`(`--llm-selector` 指定時。案C の第2層適用 `LLMSetSelector`: 候補メタデータ・依存・競合・権限・予算を 1 回の LLM 呼び出しに提示し、集合または abstain/escalate を JSON で返させる。**返答は制約修復せず生のまま評価** — LLM が制約を守れるか自体が測定対象)。全 Selector が `SelectionResult = selected | abstain | escalate` を返します。LLM 応答は `benchmarks/cache/set-selector-*.json` に保存され(git 管理外)、同じ環境での再実行はキャッシュ命中により決定的です(temperature=0)。

### 結果(min_relevance=0.55、2026-07-17 再計測。lexical 列は 2026-09-19 に絶対関連度で再測定)

| 指標 | topk(lexical) | greedy(lexical) | llm gpt-4o(lexical) | topk(hybrid) | greedy(hybrid) | llm gpt-4o(hybrid) | greedy(hybrid + 1,000 skill ノイズ) |
|------|------|------|------|------|------|------|------|
| Set F1 / Exact Match | 0.438 → 0.454 / 0% | **0.582 → 0.577 / 50% → 54%** | 0.488 / 8% | 0.667 / 0% | **0.720 / 62%** | 0.628 / 25% | 0.442 / 33% |
| Dependency Closure Rate | 29% | **100%** | **100%** | 0% | **100%** | 96% | **100%** |
| Conflict-Free / Policy-Feasible | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% |
| abstain/escalate 精度 | 0% | **100%** | **100%** | 0% | **100%** | **100%** | 25% |
| 第1層 gold recall(上限) | 66% | 66% | 66% | **100%** | **100%** | **100%** | 58% |
| 選択レイテンシ平均 | 0.03ms | 0.08ms | 約1.2秒 | 0.04ms | 0.07ms | 約1.0秒 | 0.17ms |

gpt-4o-mini は同条件でさらに低く(lexical: Set F1 0.228 / status 精度 32%、hybrid: 0.408 / 54%)、制約付き集合選択には小型モデルでは不足でした。beam は greedy とほぼ同等ですが、本再計測では hybrid で僅差に劣後(0.708 vs 0.720)— ビームが Σu 最大の集合を選んでも gold F1 最大とは限らないためです。分枝限定法(bnb)は全 28 シナリオで Σu の最適性を証明済み(平均 0.10ms)ですが、gold F1 は lexical で greedy と同一(0.582)、hybrid では beam と同一集合に到達して greedy に劣後(0.708)しました。

### 結果の読み方

- **Top-K は集合制約を系統的に破ります**: hybrid 検索下で Dependency Closure Rate 0%(agent を選ぶのに依存先の主 tool を選ばない)、Exact Match 0%。greedy は閉包 100% を維持しつつ Set F1 でも上回り、**F-RETR-04 の「集合選択」がランキング上位 K 件では代替できない**ことの直接の実証です。
- **LLM Set Selector(案C 第2層)はソルバーに勝てません**: 最良条件(gpt-4o・temperature 0・hybrid で gold recall 100%・制約と選択規約をプロンプトに明示・few-shot 付き)でも Set F1 0.628 / Exact 25% と greedy(0.720 / 62%)に及ばず、レイテンシは 4 桁大きい(約 1 秒 vs 0.07ms)。誤りの内訳は 18 件中 16 件が **gold の真部分集合への過少選択**(明示的に指示しても specialist agent や memory を落とす)で、過剰選択はゼロ。一方で制約充足はおおむね守り(閉包 96%)、abstain/escalate 判定は 100%。プロンプト開発の過程では、権限名(`kernel.read` 等)から**宣言されていない権限要求を推論して全滅する**挙動(SetF1 0.03)も観測され、「制約は宣言メタデータとして解くべきで、自然言語推論に委ねるべきでない」という案H の設計判断を裏付けました。
- **貪欲順序は閉包単位の効用合計 Σu が本質**: 候補単体スコア順の素朴な greedy は、単体で高スコアな「代替 tool」を先に取り、競合制約で本命の agent+tool+skill 連鎖を塞いでしまいます(実装時に実測: Set F1 0.375 → 単位効用順で 0.625)。
- **厳密解ソルバーでも greedy を超えません — ボトルネックは探索ではなく効用関数です**: bnb は枝刈り付き全探索で Σu の最適性を全シナリオで証明し(「proven optimal」、平均 0.10ms)、Σu では常に greedy 以上。それでも gold F1 は hybrid で 0.708 と greedy(0.720)に劣後します。唯一差が出た support シナリオでは、単体スコアの高い競合 tool(quickdraft 0.641・依存なし)が gold の workbench(0.554・skill 依存)を Σu で上回り(1.937 vs 1.850)、厳密最適化が gold から**離れる**方向に働きました。greedy の閉包単位順序は「依存で結合したリソースを一体で評価する」構造的事前分布として機能しており、これが gold と整合。第2層の探索系比較(Top-K / greedy / beam / bnb / LLM)はこれで完結し、改善の余地は探索アルゴリズムではなく **u(i,q) への構造情報の反映(案E / 実績メタデータ)** にあります。
- **棄権(15.6)は Coverage と Selective Accuracy のトレードオフ**: 関連度閾値を振ると hybrid で {rel≥0.55: Coverage 71% / abstain・escalate 100%}, {rel≥0.50: 93% / 25%}, {閾値なし: 100% / 0%}。複合スコアは trust・コスト等を含むため棄権判定には使えず、**関連度成分のみを閾値化**する必要があります。関連度が絶対値になったことで閾値は初めて「クエリによらず同じ意味」を持つようになりました(1,000 スキルでの実測: 正解の関連度 中央値 0.72 / 下位 10% 0.22、無関係タスクの 1 位 0.15〜0.52)が、**分布は依然として重なっており完全な分離はできません**。カタログごとの実測に基づく設定が前提で、ライブラリ既定値は 0.0 のままです(閾値の単位が変わったため、ベンチマークスクリプトの既定は 0.55 → 0.35 に読み替えています)。
- **第1層の gold recall が第2層の上限**(前 PR の知見の再確認): 1,000 skill をノイズ混入すると gold recall 58% に落ち、greedy でも Set F1 0.442 止まり。大規模カタログでの候補生成(案I)が次のボトルネックです。

## 案E: 能力・依存グラフによる候補補強(15.2 拡張版案E)

`--retriever graph-<base>`(`graph-lexical` / `graph-hybrid-model` など)は、ベース Retriever のシード候補を `CapabilityGraphRetriever`(`marmo_core/graph_routing.py`、ゼロ依存・決定的)で拡張します。シード上位(既定 5 件)から、宣言メタデータのエッジ(depends_on / 逆依存 / capability 名前空間の同輩)を最大 2 ホップ辿り、到達したリソースへシードの関連度を減衰付き(既定 0.8/ホップ)で継承させます。「語彙がタスクと一致しない構造的補完リソース(memory・skill・agent)」が (1) プールに入り、(2) 棄権ゲートを通る関連度を持ち、(3) 依存閉包単位の効用 Σu を押し上げる — B&B 比較で確定した「効用関数が構造を知らない」ボトルネックへの第1層側からの対処です。

| 構成 | gold recall | greedy Set F1 | Exact | 安全指標 |
|------|------|------|------|------|
| lexical → graph-lexical | 66% → 66% | 0.582 → **0.588** | 50% → **54%** | 非劣化 |
| (絶対関連度で再測定) lexical → graph-lexical | 66% → 66% | 0.577 → 0.577 | 54% → 54% | 非劣化 |
| hybrid → graph-hybrid | 100% → 99% | 0.720 → 0.720 | 62% → 62% | 非劣化 |
| hybrid+1,000ノイズ → graph | 58% → **68%** | 0.444 → **0.462** | 33% → **38%** | 非劣化 |

### 結果の読み方

- **効果は設計意図どおりノイズ下で最大**: 拡張は「シードは見つかるが仲間が候補プールから溢れる」状況を直します。クリーン hybrid(recall 100%)には改善余地がなく、同値に留まるのは想定どおりです。
- **3 つのガードが測定上必須でした**(いずれも外すと退行を実測):
  1. **偽シード抑止** — 当時の BM25 関連度は相対正規化だったため、off-catalog タスクでも 1 語の偶然一致("full" が "Full workbench tool" に当たる)が rel 0.7 のシードになりました。拡張がその依存 skill をプールに入れると、本来閉じないはずの閉包が完成し、正しい abstain が誤選択に反転(symphony シナリオ)。task トークン 2 個以上または埋め込み類似 0.55 以上の**絶対的証拠**をシード条件にして解消しています。関連度が絶対値になった現在は同じ偶然一致が rel 0.1 前後に落ちるため、このガードは二重の安全網になりました(既定値は据え置き)。
  2. **名前空間ハブ上限(12 件)** — 取り込みカタログの自由記述 capability は定型文になりがちで、distractor 1,000 skill は全件が "skill instructions" 名前空間を共有 = 全ノイズを結ぶハブと化します。上限なしではノイズシードがクラスタごとプールに雪崩れ込み、gold の workbench/agent を押し出して F1 0.444→0.415 に退行。
  3. **構造的追加候補のプール枠予約** — コーパス設計上、workbench(cost 2.0・community trust)と agent(slow)は複合スコアでノイズの完璧な trust/cost 成分に負け、拡張で到達してもプール截断で再び切り捨てられます(memory/skill だけ残り閉包が壊れる)。追加候補(既定最大 12 件)に枠を予約し、recall 62%→68%。
- **限界 = シードは作れない**: ノイズ下 paraphrase のようにドメイン内シード自体が無い場合、グラフは何も拡張できません(recall 68% の残りの欠落は全てこのパターン)。第1層のスケールボトルネックは残っており、案I(階層型)の動機がむしろ強まりました。継承関連度(シード×0.8)が棄権ゲート(0.55)近傍に落ちる**キャリブレーション結合**も今後の課題です。

## Policy アブレーション(15.6 / 安全制約の挿入位置)

`--policy-ablation` は、権限制約をパイプラインのどこで課すかを 5 条件で比較します(権限軸に分離するため、ゲートの PolicyContext は副作用エスカレーションを無効化。検索スコアの permission_fit ソフト成分は全条件共通)。

```bash
python3 benchmarks/run_set_benchmark.py --retriever hybrid-model --policy-ablation \
    --output benchmarks/results/set-selection-policy-hybrid.json
```

| 条件 | 権限の扱い | Set F1 | Policy-Feasible | status 精度 | abstain/escalate 精度 | Coverage | gate 発火 |
|------|-----------|--------|------|------|------|------|------|
| none | なし | 0.720 | 96% | 79% | 50% | 79% | — |
| gate-only | 後段 Activation Gate のみ | 0.720 | 100% | 82% | **100%** | 68% | 3 |
| **selector(既定)** | 選択器が制約として充足 | 0.720 | **100%** | **86%** | **100%** | 71% | — |
| pushdown | 検索時ハードフィルタ + 選択器 | 0.720 | 100% | 79% | 50% | 71% | — |
| full | pushdown + Gate | 0.720 | 100% | 79% | 50% | 71% | 0 |

(greedy・hybrid-model・28 シナリオ。lexical でも同じ序列。beam は greedy と同傾向、topk は制約盲目のため gate-only でのみ改善: status 精度 86%→89%)

### 結果の読み方

- **選択器内の制約充足(現行既定)が最良**です。権限不足の候補が「見える」位置で解くため、(1) 実行可能な代替を選び直せる、(2)「人間が権限を付与すれば実行可能」なケースを escalate として正しく報告できる、の両方が成立します。
- **後段ゲートだけでは再計画できません**: 権限盲目な選択が不可行なメンバーを含む集合を作ると、ゲートはブロック(escalate)しかできず、実行可能な代替が候補にあっても選び直せない(incident シナリオで実測: selector 条件は代替を選択、gate-only 条件は不要な escalate)。一方で制約推論を持たない Top-K にとっては唯一の安全網であり、gate-only で status 精度が 86%→89% に改善します。
- **検索時ハードフィルタ(pushdown)は escalate 能力を破壊します**: 権限不足の候補がプールから消えるため、「権限があれば実行可能」なシナリオが abstain に劣化(abstain/escalate 精度 100%→50%)。安全にはなるが、HITL(4.12)への正しい接続が失われる — フィルタは「早いほど良い」わけではない、という 15.6 の設計論点の直接の実証です。
- **full の後段ゲートは一度も発火しません**(pushdown 後は不可行メンバーが集合に入り得ない)— 精度への寄与はゼロで、F-GATE-01(バイパス経路を設けない)の多層防御としてのみ意味を持ちます。
- **Set F1 は全条件で不変**(0.720)。63 リソース規模では権限軸は精度ではなく**安全性(Policy-Feasible)とステータス判定**に効きます。none 条件では不可行集合の活性化が 4% 発生しました。

## cross-encoder 再ランク(15.7 項目4 / LLM 再ランクの非 LLM 比較対象)

LLM 再ランク(案C 最小)は hit@1 を大きく押し上げますが、クエリごとに LLM 呼び出し(約 2 秒・非決定的・監査はキャッシュ頼み)が発生します。同じ問い —「この候補はこのタスクをどれだけ満たすか」— を、(task, リソースメタデータ)ペアを**同時に読む**小型ローカルモデルで解けば、決定的・オフライン・API コストゼロで同等の品質が得られるのではないか、という仮説を検証しました。

```bash
python3 benchmarks/run_benchmark.py --cross-encoder                     # BM25 + cross-encoder
python3 benchmarks/run_benchmark.py --retriever hybrid-model --semantic-weight 0.9 --cross-encoder
python3 benchmarks/run_set_benchmark.py --retriever ce-lexical [--ce-weight 0.3]
```

`CrossEncoderRerankRetriever`(`marmo_core/rerank.py`)は `CrossEncoderProvider` を差し替え点とし(コアはゼロ依存のまま。fastembed 実装はベンチマーク側)、モデルのスコアを logistic で [0,1] に潰して**関連度成分に混合**します。LLM 再ランクが順位の入れ替えのみを行うのと異なり、複合スコアの policy 成分(権限・信頼度・副作用・コスト)を保ったまま、第2層の棄権ゲート(15.6 は関連度成分を閾値化)にも作用する構成です。

### ランキング品質(120 シナリオ / 1,000 リソース)

| 構成 | hit@1 | hit@5 | direct | paraphrase | recall@50 | ウォームレイテンシ |
|------|------|------|------|------|------|------|
| lexical(基準) | 61% | 76% | 90% | 29% | 90% | **3.9ms** |
| **lexical + cross-encoder** | 73% | 83% | 90% | 49% | 90% | 2141ms |
| lexical + LLM 再ランク | **79%** | 86% | 94% | **60%** | 90% | 1834ms |
| hybrid-model(基準) | 77% | 87% | 94% | 57% | 99% | **63ms** |
| **hybrid-model + cross-encoder** | 76% ⚠ | 88% | 92% | 51% ⚠ | 99% | 3220ms |
| hybrid-model + LLM 再ランク | 85% | 92% | 94% | 80% | 99% | 2448ms |
| hybrid + HyDE + LLM 再ランク | **92%** | **97%** | 98% | **86%** | 100% | 2241ms |

cross-encoder は `Xenova/ms-marco-MiniLM-L-6-v2`(fastembed / ONNX / CPU、再ランクプール 50 件)。

### 集合選択への影響(28 シナリオ / 63 リソース、greedy)

| ce 混合重み | gold recall | Set F1 | Exact | status 精度 | abstain/escalate | Coverage |
|------|------|------|------|------|------|------|
| 0.0(= lexical 基準) | 66% | **0.582** | 50% | **75%** | **100%** | 61% |
| 0.3 | 66% | 0.458 | 46% | 50% | 75% | — |
| 0.5 | 66% | 0.446 | 38% | 50% | 75% | — |
| 0.7 | 66% | 0.438 | 38% | 50% | 75% | — |
| 1.0(既定) | 66% | 0.431 | 38% | 50% | 75% | 39% |

### 結果の読み方

- **弱い基盤は救うが、強い基盤には効かない**: BM25 単体では hit@1 61%→73%(paraphrase 29%→49%)と大きく改善する一方、**案B hybrid の上では改善ゼロ**(77%→76%、paraphrase はむしろ 57%→51% と劣化)。埋め込みが既に意味的な近さを捉えている場合、ms-marco 系 cross-encoder が上乗せできる情報は残っていません。LLM 再ランクには全条件で届きませんでした(最良比較: 76% vs 92%)。
- **CPU 上では「安い代替」にならない**: 候補 50 件のスコアリングに約 1〜3 秒かかり、LLM 再ランク(約 1.8〜2.4 秒)と同等かそれ以上です(8 コア WSL2 / ONNX)。cross-encoder の優位性は速度ではなく、**決定性・オフライン動作・API コストゼロ**の 3 点に限られます。GPU があれば速度面の結論は変わり得ます。
- **第2層では劣化する — 原因は順位ではなく較正**: gold recall は全条件で同一(66%。再ランクはプールの中身を変えないため当然)にもかかわらず Set F1 は 0.582→0.431 に低下し、Coverage も 61%→39% に落ちます。つまり**正しい候補は入っているのに選ばれなくなる**。混合重みを下げても解消せず単調に悪化し、0.3 でも abstain/escalate 精度は 100%→75% に落ちます。cross-encoder スコアの分布が、関連度 0.55 に較正された棄権ゲート(15.6)と噛み合っていないためで、案E で積み残した**較正結合の課題が別の層で再現**した形です。再ランクを第2層と併用するなら、閾値の再較正がセットで必要になります。
- **設計上の含意**: 「関連度成分を差し替える」タイプの改良は、第1層のランキング指標だけで採否を決められません。棄権ゲートを共有している以上、第2層の Coverage / Selective Accuracy まで見て初めて可否が決まる、という運用則が実測で確認できました。

## 案I: 階層型・粗密ルーティング(15.2 / 10k〜100k スケール)

「1万件以上のカタログでも精度・レイテンシ・コンテキストコストを維持してルーティングできる」(12.1 の中心的主張 2)を検証します。`generate_scale_corpus.py` が決定的な合成カタログ(ドメイン → プロバイダ → 5 リソース族の階層。gold コーパスと同一構造の依存・競合付きなので、ノイズが構造的に見分けられない設計)を生成し、`run_scale_benchmark.py` が gold 28 シナリオ + cross-domain 6 シナリオ(gold 集合が 2 ドメインに跨る)で flat と階層型を比較します。カタログ JSON は決定的に再生成できるためコミットしません。

```bash
python3 benchmarks/run_scale_benchmark.py --size 10000    # 全構成(要 fastembed)
python3 benchmarks/run_scale_benchmark.py --size 100000 \
    --retrievers lexical,hier-namespace-lexical,hier-provider-lexical
```

`hier-<戦略>-<基盤>` は `HierarchicalRetriever` で、第1段(coarse)がグループを BM25(hybrid 基盤ではグループ重心コサインとの混合)でランキングして上位 `route_k`(既定 3)を選び、第2段(fine)が選ばれたグループのメンバーだけに基盤 Retriever を適用します。グループ構築戦略は capability 名前空間(`namespace`)/ プロバイダ・MCP サーバー単位(`provider`)/ 権限境界(`permission`)/ 記述埋め込みの k-means(`embedding`)の 4 種です。

### 10,063 リソース(gold 63 + 合成 10,000 / 200 ドメイン・73 プロバイダ / greedy・pool 50・route_k 3)

| 構成 | gold recall@50 | Set F1(通常/cross) | Exact | status 精度 | abstain/escalate | p50 / p95 | 走査割合 | Cluster Recall(実測/oracle) |
|------|------|------|------|------|------|------|------|------|
| lexical(flat) | 64% | 0.617(0.565 / 0.822) | 50% | 82% | 100% | 6.1ms / 49.5ms | 100% | — |
| hybrid-model(flat) | 64% | 0.550(0.519 / 0.671) | 30% | 88% | **50% ⚠** | **1036ms / 1199ms ⚠** | 100% | — |
| hier-namespace-lexical | 60% | 0.537(0.480 / 0.767) | 37% | 79% | 100% | 6.4ms / 18.9ms | 18.3%※ | 80% / 100% |
| hier-provider-lexical | 60% | 0.571(0.511 / 0.811) | 40% | 82% | 100% | 14.9ms / 91.1ms | 19.3%※ | 80% / 100% |
| hier-permission-lexical | 64% | 0.617(0.565 / 0.822) | 50% | 82% | 100% | 90.5ms / 1663ms | 94.5% ⚠ | 100% / 100% |
| hier-embedding-lexical | 37% ⚠ | 0.263(0.243 / 0.343) | 3% | 82% | 100% | 24.3ms / 40.0ms | 20.9%※ | 57% / 72% ⚠ |
| **hier-namespace-hybrid-model** | **69%** | **0.589(0.524 / 0.848)** | **47%** | **94%** | **100%** | **24.1ms / 31.3ms** | **0.9%** | 78% / 100% |
| hier-provider-hybrid-model | 67% | 0.552(0.506 / 0.735) | 33% | 94% | 100% | 44.0ms / 103.7ms | 3.2% | 80% / 100% |
| hier-embedding-hybrid-model | 35% ⚠ | 0.241(0.226 / 0.300) | 3% | 91% | 100% | 51.7ms / 85.6ms | 4.0% | 39% / 72% ⚠ |

※ lexical 基盤の走査割合はゼロシグナル時の flat フォールバック(6 シナリオ、走査 100% 扱い)を含む平均。ルーティングが成立したクエリに限ると namespace は約 0.8%。

### 100,063 リソース(lexical 系のみ。hybrid の flat 全件コサインは 10k 時点で既に不成立)

| 構成 | gold recall@50 | Set F1 | Exact | p50 / p95 | 走査割合 | Cluster Recall(実測/oracle) |
|------|------|------|------|------|------|------|
| lexical(flat) | 64% | 0.617 | 50% | 37.8ms / **808.6ms ⚠** | 100% | — |
| hier-namespace-lexical | 60% | 0.549 | 40% | 18.1ms / **52.3ms** | 17.9%※ | 80% / 100% |
| hier-provider-lexical | 60% | 0.591 | 43% | 56.0ms / 273.8ms | 19.0%※ | 80% / 100% |

**字句検索の枝刈り後の再測定**: `LexicalRetriever` が合成スコアの上界で採点を打ち切るようになった後、同じ 100,063 件・34 シナリオ・`min_relevance` 0.35 で main（59275d58）と比べました。flat lexical の p50 は 40.0 → 15.1ms、p95 は 839.0 → 101.5ms、平均は 148.4 → 21.4ms です。Set F1 0.595 をはじめ品質指標はすべて同一でした（[`results/scale-lexical-100000-before.json`](results/scale-lexical-100000-before.json) / [`-after.json`](results/scale-lexical-100000-after.json)）。上の 100k 表は来歴の記録がない旧版（相対関連度・`min_relevance` 0.55）の測定で、比較のためそのまま残しています。

### 結果の読み方

- **中心的主張 2 の実証(10k)**: flat hybrid の全件コサイン走査は 10k で p50 約 1 秒に達し成立しません。namespace 階層化は走査を **0.9%** に削減して p50 24ms(**43 倍**)としつつ、gold recall 69% vs 64%・Set F1 0.589 vs 0.550・status 精度 94% vs 88% と**品質でも flat を上回ります**(ルーティングがノイズ 10,000 件を候補プールから構造的に排除するため)。ANN インデックスなし・ゼロ追加依存でこれを達成できるのが案I の価値です。
- **ノイズ下の棄権が階層化で回復**: flat hybrid は off-catalog タスク(交響曲の作曲など)にノイズが意味的に当たり abstain/escalate 精度が 50% に崩壊します。階層化はプールが小さく無関係なため棄権ゲートが正しく機能し、全階層構成で 100% を維持します。
- **グループ構築は宣言 taxonomy が最良、学習クラスタは不成立**: k-means(embedding 戦略)は「記述が似たもの」を束ねるため、依存で結ばれた gold の 4 種セット(memory/skill/tool/agent は記述が異なる)を**別クラスタに分断**します(oracle cluster recall 72% — 分割自体の上限が低い)。ルーティングの分割は依存閉包と整合する宣言メタデータ(capability 名前空間・プロバイダ)から作るべきで、案E と同じ「構造は宣言から、言語類似からではない」という結論です。permission 境界は public が 94.5% を占めルーティングには無効(権限は 15.6 のとおり選択器内の制約として扱うのが正)。
- **cross-domain は多段誤り伝播の懸念に反して flat より改善**(0.848 vs 0.671): route_k=3 が両ドメインのグループを拾い、かつ各グループ内はノイズが少ないためです。単一ドメインタスク(通常 28 件)では cluster recall 80% vs oracle 100% の**第1段ルーティング誤り(主に paraphrase)が残存ボトルネック**で、Set F1 の flat lexical との差(0.537〜0.571 vs 0.617)もここから来ています。
- **100k でもルーティング精度は劣化しない**: cluster recall・Set F1 は 10k→100k でほぼ不変(誤りはカタログサイズではなくドメイン数と言い回しに依存)。flat lexical は p95 808ms へ劣化する一方、hier-namespace は p95 52ms に留まります(15 倍)。BM25 の p50 は 100k でも 38ms であり、**lexical 基盤に限れば flat が精度で優位**という関係は保たれます — 階層化の主価値は埋め込み系検索のスケール成立にあります。
- **ウォームアップ**: hybrid 系はカタログ全件の埋め込み計算(10k 件で約 272 秒、CPU / bge-small)を初回のみ要します。プロセス内で全構成が同じ埋め込みメモを共有するため 2 構成目以降は数秒です。

## 第3層(適応): ルーティングキャッシュ案F と実行フィードバック(15.4 / F-LOG-08)

第1・2層は静的で、毎回ゼロから集合を導出します。第3層は「過去の実行から次回の選び方をどう改善するか」を問うため、単発のシナリオ走査ではなく**トラフィックのリプレイと、タスクごとの観測結果**を必要とします。`run_adaptive_benchmark.py` はその両方を用意し、あわせて 15.7 が要求する End-to-end 指標(Task Success Rate)を導入します。

```bash
python3 benchmarks/run_adaptive_benchmark.py --retriever lexical --epochs 3
python3 benchmarks/run_adaptive_benchmark.py --retriever hybrid-model --cache-embeddings model --epochs 3
python3 benchmarks/run_adaptive_benchmark.py --retriever hybrid-model --cache-embeddings model \
        --threshold-sweep 0.30,0.40,0.50,0.60,0.72          # 類似度ゲートのスイープ(4 シード平均)
python3 benchmarks/run_adaptive_benchmark.py --drift-probe   # レジストリ変更による事例の陳腐化
python3 benchmarks/run_adaptive_benchmark.py --feedback --epochs 5   # 実績メタデータの書き戻し
```

### Task Success Rate は**シミュレーション**である

28 シナリオを実際に実行するには 28 個の実バックエンドが要るため、成否はルーティング結果から明示的な充足モデルで導出しています(レポートの `task_success_model` に明記)。

- `selected` シナリオ: 選択集合が **gold の上位集合**であり、かつ依存閉包が閉じ、権限的に実行可能なら成功。余剰リソースはコンテキストコストであって不正解ではない、という立場です。
- `abstain` / `escalate` シナリオ: 期待どおりの status を返せば成功。**正しく断ることが成功**です(15.6)。

決定的であることが重要で、同じルーティング判断が常に同じフィードバック信号を生むからこそ、エポック間の差を学習に帰属できます。

### 実験1: ルーティングキャッシュの構成比較(3 エポック × 28 シナリオ、seed 7)

`hybrid-model` 基盤(第1層は案B、第2層は greedy):

| 構成 | TSR | ヒット率 | Set F1 | status 精度 | p50(ヒット / ミス) | regret | 事例数 |
|------|------|------|------|------|------|------|------|
| no-cache(基準) | 0.679 | — | 0.720 | 86% | 2.619ms(— / 2.619) | — | — |
| **cache-lexical** | 0.679 | 45% | 0.720 | 86% | 2.209ms(**0.081** / 2.559) | 0 | 19 |
| cache-semantic | 0.679 | 45% | 0.720 | 86% | 2.269ms(0.719 / 2.983) | 0 | 19 |
| cache-poisoned(失敗も保存) | 0.679 | 45% | 0.720 | 86% | 2.169ms(0.109 / 2.644) | 0 | 28 |
| cache-stale-blind(版チェック無効) | 0.679 | 45% | 0.720 | 86% | 2.225ms(0.080 / 2.447) | 0 | 19 |

`lexical` 基盤では no-cache p50 0.071ms に対しヒット 0.054ms(パイプラインが元々安いため利得は消える)。

### 実験2: 類似度ゲートのスイープ(hybrid-model + モデル埋め込み、4 シード平均 [最小-最大])

| 閾値 | 構成 | ヒット率 | TSR | Set F1 | status 精度 | regret / rescue |
|------|------|------|------|------|------|------|
| 0.30 | cache-semantic | 54% | 0.607 [0.595-0.619] ⚠ | 0.610 | 92% | 49 / 25 |
| **0.40** | **cache-semantic** | **60%** | **0.744 [0.714-0.774]** | **0.731** | **91%** | 21 / **43** |
| 0.50 | cache-semantic | 50% | 0.699 [0.667-0.714] | 0.744 | 90% | 3 / 10 |
| 0.60〜0.72 | cache-semantic | 45〜47% | 0.679(基準と同一) | 0.720 | 86% | 0 / 0 |
| 0.30 | cache-lexical | 49% | 0.670 [0.643-0.702] ⚠ | 0.698 | 89% | 13 / 10 |
| 0.40〜0.72 | cache-lexical | 45〜47% | 0.679(基準と同一) | 0.720 | 86% | 0 / 0 |

### 実験3: レジストリ変更(cached リソースの 25% を 2.0.0 に再公開、`side_effect` を irreversible へ昇格)

| admission 規則 | TSR | ヒット率 | stale ミス | stale 事例の再利用 | **unsafe replays** |
|------|------|------|------|------|------|
| version-checked(既定) | 0.571 | 25% | 9 | 0 | **0** |
| id-only | 0.571 | 57% | 0 | 9 | **9 ⚠** |

### 実験4: 実行フィードバック(5 エポック、lexical、`ExecutionEvaluator` の書き戻し)

| 条件 | TSR | Set F1 | Exact | エポック別 TSR |
|------|------|------|------|------|
| static | 0.571 | 0.582 | 50% | 0.571 / 0.571 / 0.571 / 0.571 / 0.571 |
| **feedback** | **0.600** | **0.607** | 53% | 0.571 / **0.607** / 0.607 / 0.607 / 0.607 |

### 結果の読み方

- **キャッシュは既定構成では「速いだけ」— 品質は動かない**: 逐語的な再訪では replay はパイプラインと同一集合を返すため、TSR・Set F1・status 精度はすべて基準と一致し regret は 0 です。効くのはレイテンシで、hybrid 基盤ではヒット時 **0.081ms vs 2.6ms(32 倍)**。ただし**パイプラインが安ければ利得も消えます**(lexical 基盤では 0.054ms vs 0.071ms)。案F の価値は第1層のコストに比例します。
- **閾値を下げると、キャッシュは初めて品質装置になる**: モデル埋め込みの事例索引を **t=0.40** で運用すると、TSR が **0.679 → 0.744**(全 4 シードで基準超え)、status 精度 86% → 91% に上がります。仕組みは明快で、**言い換えクエリが、直接表現の兄弟クエリが成功させた集合をそのまま継承する**ためです(rescue 43 > regret 21)。第1層が最も弱いのは言い換えであり(no-cache の paraphrase TSR は 0.25)、そこをキャッシュが埋めます。t=0.30 まで下げると無関係な事例まで再利用され崩壊します(TSR 0.607 / regret 49)。
- **語彙一致の事例索引では汎化しない**: cache-lexical は t≥0.40 で常に基準と同一(逐語再訪しか当たらない)、t=0.30 では regret が rescue を上回って劣化します。**キャッシュの汎化能力は埋め込みが担っており、語彙類似では安全に閾値を下げられません**。代償は 1 クエリあたり約 0.6ms のコサイン計算です(ヒット時 0.719ms vs 0.081ms)。
- **陳腐化は「事故」ではなく既定で起きる**: 25% の再公開で id-only 規則は **9 件の unsafe replay** を生みました — 選択器が `side_effect=read` として承認した集合が、`irreversible` に昇格したリソースを含んだまま返ります。`id@version` で照合する既定規則はこれを 0 に抑えますが、ヒット率は 57% → 25% に下がります。**キャッシュの正しさはヒット率と直接トレードオフの関係にあり**、リビジョン番号では粗すぎます(無関係な `add` でも全流しになる)。なお Activation Gate(F-GATE-01、12.1 で常設と決着)は最後の砦として依然機能しますが、版チェックは「そもそもゲートに危険な集合を渡さない」ための層です。
- **失敗事例の保存は無害だが無益**: cache-poisoned は失敗ルーティングも事例化しますが、admission が `failed-case` として弾くため再利用されません(ミス理由 18 件)。事例数だけが 19 → 28 に増えます。失敗の記録に意味があるのは案D(その失敗を効用の学習信号に使う)であって、案F の再利用ではありません。
- **フィードバックループは閉じており、効果は小さいが実在する**: `ExecutionEvaluator` の書き戻しで TSR 0.571 → 0.600、Set F1 0.582 → 0.607。改善は**エポック1で頭打ち**(以降不変)で、内訳を見ると direct は 0.875 のまま、**paraphrase だけが 0.167 → 0.233** と動いています。合成スコアにおける `success` の重みが 0.05 しかないため、拮抗した候補の順位しか入れ替わらないためです。B&B の結論(ボトルネックは探索ではなく効用関数 u(i, q))に照らすと、これは**案D が触るべき場所が正しい**ことの確認であり、同時に**固定重み 0.05 の一成分では足りない**ことの確認でもあります。
- **限界**: TSR はシミュレーションであり、実バックエンドの失敗(タイムアウト・スキーマ不一致・外部 API エラー)は含みません。またトラフィックは 28 シナリオの反復で、実運用のロングテール分布ではありません。案F のヒット率は**タスクの反復率に完全に依存**するため、ここでの 45〜60% を運用値として読むことはできません。

## 独立 test・実行結果・敵対的メタデータ

上の 120 件と 28 件の既存評価は、設定探索にも使った探索的な結果です。`run_evidence_benchmark.py` は別の小規模な評価を追加します。`evidence_cases.json` の各タスクには `dev` / `test` と固有のタスク系列 `family` を付け、同じ系列が両方へ入らないことを検査します。dev の実行結果だけを `CaseBasedRouter` に記録し、test は固定したまま一度評価します。コーパスは同梱の Memory / Tool / Agent と、`examples/resources/core_resources.json` にある 2 つの Skill です。gold 集合は個々のタスクに対して明示しています。

```bash
python3 benchmarks/run_evidence_benchmark.py
```

Tool タスクでは、選択された Tool だけを通常の activation / execution gate を通して**同梱の実ハンドラ**で実行します。加えて `Kernel.run_goal` も固定した Tool 呼び出し応答で動かし、公開 API の経路から作成物を確認します。各ケースに新しい一時ワークスペースを作り、書き込み Tool はその対象 ID だけを事前承認します。Tool の `status=success` と、ファイル内容・ZIP の収録物・戻り値を別々に検査します。`tool_success_rate_conditional` の分母は実際に呼んだ Tool、`task_completion_rate` の分母は Tool が必要な全タスクです。後者では、正しい Tool が選ばれず実行しなかったケースを失敗に含めます。LLM の Tool 選択・引数生成・最終回答は固定応答なので、この値は単一ステップの Tool タスク達成率であり、実モデルを使ったエージェント全体の完了率や HITL の承認品質ではありません。

| 固定 test (10 件、うち Tool タスク 6 件) | baseline | dev 実行から学習した cache |
|---|---:|---:|
| Set F1 / Exact | 0.704 / 37.5% | 0.704 / 37.5% |
| abstain / escalate 精度 (各1件) | 2/2 | 2/2 |
| Tool 成功率 (実行した 5 件) | 5/5 | 5/5 |
| タスク達成率 (Tool タスク 6 件) | 5/6 | 5/6 |
| `Kernel.run_goal` 経由のタスク達成 | 5/6 | — |
| cache hit | — | 0/10 |

dev の同系列再訪では 8 Tool タスク中 2 件が cache に命中し、実行成果物も正しく得られました。一方、固定 test の別系列では 0/10 件で、一般化は確認できません。既定の語彙類似度閾値 0.72 では別系列に命中しないため、合成の反復トラフィックで得たヒット率を実運用値として扱えません。ケース数が小さく、gold は第三者による独立アノテーションではなくこのリポジトリで作ったものなので、信頼区間や一般化性能の主張には使いません。

同じ固定 test の 6 Tool タスクに、通知 Tool の説明を各タスクの語で埋める敵対的メタデータを混入させます。`keyword_stuffing` と `instruction_payload` は `trust_level=untrusted` のまま、`metadata_forgery` は信頼・権限・副作用・隔離レベルの宣言まで偽装します。前二者は 6 件とも選ばれず、activation gate の判定も deny でした。後者では 6/6 件で偽装 Tool が選択され、activation gate も通過可能でした。**実ハンドラの危険な実行は行っていません**。これはメタデータ宣言自体の真正性をコア単体では確認できないことを示す攻撃候補の測定で、実際の被害件数ではありません。詳細は `benchmarks/results/evidence.json` の `adversarial_test` を参照してください。

### 偽装メタデータの継続計測

上の 6 件は Tool だけで、偽装も 4 項目をまとめて変えています。`run_forgery_benchmark.py` は、どの宣言の偽装がどの段階まで届くかを、検索・選択・ルーティングを変えるたびに同じ形で測ります。

```bash
python3 benchmarks/run_forgery_benchmark.py            # 約 90 秒、LLM なし
```

- **ケース**: `evidence_cases.json` の 22 件（dev / test、abstain 2・escalate 2 を含む）と、集合選択コーパス（63 資源）の 28 シナリオ（abstain 2・escalate 2）。
- **偽装資源**: Tool・Skill・Agent それぞれに 1 つ。本文は 2 通りです。`stuffed` はタスク文を 5 回繰り返した説明（従来の 6 件と同じ）、`clone` は同じ種別の gold 資源の名前・説明・能力・タグの複製（gold にその種別があるケースだけ）。
- **宣言**: 正直な宣言は「未審査の第三者が外部へ送信する資源」（`trust_level=untrusted`、`net.external` と `message.send`、`side_effect=external`、Tool は `isolation_level=L3`）です。偽装は各項目を `verified` / 権限なし / `none` / `L0` に置き換え、Tool は 4 項目、Skill と Agent は 3 項目の**全組み合わせ**（16 / 8 通り）を測ります。
- **到達段階**: 候補に入る → 選択される → activation gate が allow → `Kernel.run_goal` がモデルに渡す（Tool / Agent はツール定義、Skill は本文がプロンプトに入る）→ モデルが呼べば execution gate を通ってハンドラが実行される。モデルは「渡された偽装資源を必ず呼ぶ」固定応答なので、測っているのはゲートで、モデルが偽の説明に従うかどうかではありません。偽装資源のハンドラは `ResourceActivator` で差し込んだ**何もしない記録用の関数**で、同梱の実ハンドラは偽装資源からは一度も動きません。
- **被害の指標**: gold の押しのけ（偽装なしでは選ばれていた同じ種別の gold が外れる）、gold Tool の喪失（偽装なしではモデルに渡っていた gold Tool が渡らなくなる）、状態の変化、abstain / escalate の乗っ取り（abstain・escalate が正解のケースで偽装資源を含む `selected` になる）。

結果は [`results/forgery.json`](results/forgery.json)（2,656 変種 × 3 構成）。`tracked` が変更前後で比べる固定の項目で、`legacy_baseline` に従来の 6 件（`metadata_forgery` 6/6）を同じ実行で再測定して残しています。

| 構成 | 種別 | 宣言 | 選択 | activation 通過 | モデルに渡る | ハンドラ実行 | gold Tool 喪失 | 乗っ取り |
|---|---|---|---:|---:|---:|---:|---:|---:|
| lexical + greedy | Tool | 正直 | 0.000 | 0.000 | 0.000 | 0.000 | 0.231 | 0.000 |
| lexical + greedy | Tool | 全偽装 | 0.534 | 0.534 | 0.534 | 0.534 | 0.692 | 1.000 |
| lexical + greedy | Tool | 一部だけ偽装 | 0.226 | 0.000 | 0.000 | 0.000 | 0.374 | 0.500 |
| lexical + greedy | Skill | 全偽装 | 0.526 | 0.526 | 0.526 | — | 0.231 | 1.000 |
| lexical + greedy | Agent | 全偽装 | 0.564 | 0.564 | 0.564 | 0.564 | 0.231 | 1.000 |
| lexical + 被覆型 | Tool | 全偽装 | 0.534 | 0.534 | 0.534 | 0.534 | 0.692 | 1.000 |
| lexical + Kernel 既定（rule-based） | Tool | 正直 | 0.420 | 0.000 | 0.000 | 0.000 | 0.231 | 0.875 |
| lexical + Kernel 既定（rule-based） | Tool | 全偽装 | 0.784 | 0.784 | 0.784 | 0.784 | 0.692 | 1.000 |
| lexical + Kernel 既定（rule-based） | Skill | 全偽装 | 0.859 | 0.859 | 0.859 | — | 0.231 | 1.000 |
| lexical + Kernel 既定（rule-based） | Agent | 全偽装 | 0.833 | 0.833 | 0.833 | 0.833 | 0.231 | 1.000 |

Skill と Agent の「正直」は 3 構成とも activation 通過 0、Skill にハンドラはありません（—）。乗っ取りの分母は abstain / escalate が正解の 8 ケース × 変種で、rule-based は偽装なしでも abstain しない Selector なので値が高く出ます。gold Tool 喪失の分母は偽装なしで gold Tool がモデルに渡っていた evidence の Tool タスクです。

**読み方**

- **止めているのは activation gate で、Selector ではありません**。greedy と被覆型は宣言された権限が足りない資源を選ばないので、権限の宣言だけを偽装した Tool（信頼度は `untrusted`、副作用は `external` のまま）は stuffed で 74%（両スイート合計。全偽装は 82%）選ばれ、activation gate で拒否されます。Selector は信頼度・副作用・隔離レベルを見ません。ゲートを通るのは 4 項目すべてを偽装した場合だけで、1 項目でも正直なら activation 通過は 0 でした（stuffed の Tool 16 通り）。
- **拒否されても被害は残ります**。選ばれてから拒否された偽装資源は gold を押しのけたままなので、一部だけ偽装した Tool でも gold Tool の喪失は 37% です（`tracked` の `partial_forgery`）。正直な宣言の stuffed Tool でさえ、greedy は「権限だけで阻まれた上位の単位」として escalate を返し（権限不足の上位候補を escalate する既定の挙動）、gold Tool が 46% のケースで渡らなくなります（clone では 0%、表の「正直」の 0.231 は両方の平均）。人に `net.external` と `message.send` の付与を求める経路でもあります。
- **`clone`（正規の資源の複製）は stuffed より通りにくい**。同点の gold と並ぶため、全偽装でも Tool 36%（evidence）、集合コーパスでは 4% でした。
- Kernel 既定の rule-based Selector は権限を見ないので、正直な宣言の偽装資源も 42〜58% 選ばれます（ゲートで拒否）。
- 宣言の真正性を確かめる対策（署名・出所の検証）はこのベンチマークの対象外です。対策を入れたら、同じコマンドで `tracked` の全偽装の行が下がるかを確かめます。

**検索・選択・ルーティングを変える PR での手順**: 変更前のブランチと変更後のブランチで `python3 benchmarks/run_forgery_benchmark.py --output /tmp/forgery-before.json`（後は `-after.json`）を実行し、`tracked.<構成>.tracked.<種別>.{honest,full_forgery,partial_forgery,any_forgery}` の `selection_rate`、`activation_reach_rate`、`execution_reach_rate`、`gold_tool_loss_rate`、`abstain_escalate_hijack_rate` を PR 本文に並べます。新しい Retriever / Selector は `CONFIGS` に足してから測ります。結果 JSON を更新する場合はこの表も揃えます。

## 100k の flat ANN 比較

`run_ann_scale_benchmark.py` は、同じ 100,063 件・34 シナリオ・埋め込み・BM25 候補・混合重み 0.9・候補枠 50・greedy Selector で、flat ANN (USearch、cosine/HNSW) と namespace 階層型を比較します。ANN はベンチマーク専用の `benchmark-ann` extra に置き、実行時依存には加えません。

```bash
python -m pip install -e '.[benchmark-ann]'
python3 benchmarks/run_ann_scale_benchmark.py --size 100000 --embedding hash
python -m pip install -e '.[benchmark]'
python3 benchmarks/run_ann_scale_benchmark.py --size 100000 --embedding model
```

`hash` は高速にスケール経路を確認するための**非意味的な対照**です。意味検索の優劣は `model` の測定で判断します。索引構築時間には埋め込み計算を含め、ウォーム検索時間と分けて記録します。既存の `scale-routing-100000.json` は `min_relevance=0.55`、現行の既定値は 0.35 なので、新しい結果と数値を直接引き算しません。

| 100k / hash-64 | gold recall@50 | Set F1 | p50 / p95 |
|---|---:|---:|---:|
| flat ANN | 0.354 | 0.249 | 55.3 / 401.1 ms |
| hier-namespace | 0.254 | 0.143 | 140.6 / 419.3 ms |

| 100k / BAAI/bge-small-en-v1.5 | gold recall@50 | Set F1 | p50 / p95 |
|---|---:|---:|---:|
| flat ANN | 0.475 | 0.471 | 45.7 / 260.7 ms |
| hier-namespace | **0.554** | **0.558** | 73.0 / **105.3 ms** |

hash 対照では flat ANN が両品質指標で上回り、p50 / p95 も階層型より短くなりました。実埋め込みでは階層型が recall を 0.079、Set F1 を 0.087 改善し、p95 も 155.4ms 短くなりました。flat ANN は p50 が 27.2ms 短いため、実埋め込みでも中央値レイテンシでは有利です。hash は非意味的な対照なので、意味検索の結論は BGE の行を使います。34 シナリオの限定された評価であり、他の埋め込みモデルやカタログ分布への一般化は未確認です。

BGE を使った flat ANN の初回 index 構築は、埋め込み計算込みで 2,953.6 秒(約49.2分)、index 自体は 286,262,656 bytes(約273 MiB)でした。これは本測定機での cold build で、ウォーム検索レイテンシとは分けています。全値は同一実行の [`ann-scale-model-100000.json`](results/ann-scale-model-100000.json) に記録しています。

## ToolRet: 公開ベンチマークでの大規模・複数ツール選択

ここまでの評価は、このリポジトリで作ったコーパスとラベルを使っています。`run_toolret_benchmark.py` は、第三者が作った公開ベンチマーク **ToolRet**（Shi et al., ACL 2025 Findings、"Retrieval Models Aren't Tool-Savvy"）で第1層と第2層を測ります。ToolRet は 35 の公開ツール利用データセットを統合したもので、ツール 44,453 件、クエリ 7,961 件です。ToolBench、ToolLens、Tool-Be-Honest、ReverseChain などは**複数ツールの正解集合**を持つため、「大規模カタログから、必要な組み合わせを過不足なく選べるか」を自作ラベルなしで測れます。

```bash
python -m pip install -e '.[benchmark,benchmark-toolret]'                       # fastembed と pyarrow（ベンチマーク専用）
python3 benchmarks/run_toolret_benchmark.py --download --retrievers lexical     # 取得と字句検索
python3 benchmarks/run_toolret_llm_stages.py --stage decompose                   # LLM 分解のキャッシュ作成（Claude Code CLI）
python3 benchmarks/run_toolret_llm_stages.py --stage select --stage rerank       # LLM 集合選択・再ランクのキャッシュ作成
python3 benchmarks/run_toolret_benchmark.py --per-subset 60 \
    --retrievers hybrid-0.5,lexical,dense,hybrid-0.9,rrf,clause:hybrid-0.5,llm-rrf:hybrid-0.5,llm!:hybrid-0.5,llm:hybrid-0.5,rerank:llm!:hybrid-0.5
```

**データの扱い**: データセットカードにライセンスの記載がなく、出典ごとにライセンスが異なるため、データは再配布しません。`--download` が HuggingFace から `benchmarks/data/toolret/`（git 管理外）へ取得します。コミットするのは集計値の `results/toolret.json` だけです。

**プロトコル**

- 各サブセットから最大 60 件（seed 0）、計 1,689 クエリ（うち複数ツール 726 件）。毎回 **44,453 件の全ツール**に対して検索します。
- 指標は ToolRet と同じ nDCG@10、Recall@10、Completeness@10（正解ツールが全部上位 10 件に入った割合）。集合選択の入力上限を見るため @100 も出します。サブセットごとの平均を平均した macro 値（ToolRet の慣例）を主に使います。
- ツール文書は `toolret.tool_resource` で Tool resource に変換し、権限・信頼度・副作用・コストを全件同一にしています。順位は本文の関連度だけで決まります。
- 埋め込みは `sentence-transformers/all-MiniLM-L6-v2`（fastembed / ONNX / CPU、ToolRet の評価対象モデルの 1 つ）。埋め込み用テキストは先頭 512 字です。`bge-small-en-v1.5` はこの環境で 512 字の文書を 4 件/秒しか処理できず、44k 件に数時間かかるため使っていません。
- LLM を使う段（分解・再ランク・集合選択）は、ライブラリの `LLMQueryDecomposer`、`LLMRerankRetriever`、`LLMSetSelector` をそのまま Claude Sonnet（Claude Code CLI 経由、`benchmarks/_claude_cli.py`）で動かし、応答を `benchmarks/cache/` に保存して採点時は再生します。応答は再現しないため、キャッシュを消すと数値は変わります。
- **調整は dev、報告は test**: クエリ id の SHA-1 で 50/50 に分け、融合重み・`min_gain`・意味重みなどは dev で選んで test の値を報告します。差の信頼区間は test 上の対応のあるブートストラップ（2,000 回、95%）です。

### 第1層: 順位付け（1,689 クエリ、macro）

[`results/toolret.json`](results/toolret.json)。`llm:` は `LLMQueryDecomposer` による分解と blend 融合（下位タスク重み 0.25、既知語率による割引あり）、`llm!:` は割引なし、`llm-rrf:` は RRF 融合、`clause:` は規則ベース分解、`rerank:` は上位 30 件を `LLMRerankRetriever` で並べ替えたものです。差は test 分割での hybrid-0.5 との差です。

| 構成 | nDCG@10 | Recall@10 | C@10 | C@100 | 複数ツール C@10 | test nDCG@10 の差 [95% CI] | test C@10 の差 [95% CI] | p50 / p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `lexical`（BM25F） | 0.211 | 0.276 | 0.205 | 0.328 | 0.065 | −0.038 [−0.053, −0.025] | −0.035 [−0.055, −0.015] | 16.9 / 71.5 |
| `dense`（MiniLM-L6） | 0.205 | 0.271 | 0.199 | 0.374 | 0.077 | −0.045 [−0.059, −0.030] | −0.037 [−0.056, −0.018] | 35.9 / 120.9 |
| `hybrid-0.9` | 0.220 | 0.286 | 0.212 | 0.388 | 0.080 | −0.031 [−0.043, −0.018] | −0.030 [−0.048, −0.012] | 25.3 / 89.5 |
| `rrf`（BM25F + dense） | 0.242 | 0.326 | 0.243 | 0.412 | 0.095 | −0.013 [−0.021, −0.004] | −0.004 [−0.015, 0.008] | 41.5 / 145.3 |
| **`hybrid-0.5`（基準）** | 0.256 | 0.330 | 0.247 | 0.412 | 0.102 | — | — | 35.3 / 132.9 |
| `clause:hybrid-0.5` | 0.254 | 0.328 | 0.239 | 0.413 | 0.099 | +0.005 [−0.000, 0.010] | −0.001 [−0.011, 0.008] | 75.6 / 275.0 |
| `llm-rrf:hybrid-0.5` | 0.242 | 0.328 | 0.248 | **0.445** | 0.089 | −0.011 [−0.021, −0.001] | +0.000 [−0.014, 0.014] | 43.5 / 241.3 |
| `llm!:hybrid-0.5` | 0.271 | 0.348 | 0.259 | 0.416 | 0.105 | +0.018 [0.011, 0.025] | +0.011 [0.000, 0.022] | 59.3 / 357.9 |
| **`llm:hybrid-0.5`** | 0.271 | 0.348 | 0.259 | 0.419 | 0.105 | **+0.019 [0.012, 0.026]** | **+0.012 [0.001, 0.023]** | 35.2 / 183.9 |
| `rerank:llm!:hybrid-0.5` | **0.292** | **0.366** | **0.275** | 0.416 | **0.118** | **+0.043 [0.031, 0.054]** | **+0.027 [0.013, 0.042]** | 36.6 / 227.7 |

レイテンシは LLM 呼び出しを含みません（応答はキャッシュから再生）。実運用では分解と再ランクにそれぞれ 1 回のモデル呼び出しが加わります。

### 第2層: 集合選択（test 分割 856 クエリ）

候補プールは各 Retriever の上位 100 件、`llm-set` は上位 20 件を `LLMSetSelector`（Claude Sonnet）に見せたものです。差は同じ Retriever の top-1 との差です。

| Retriever | 選択 | Set F1 | 複数ツール F1 | Exact | 平均サイズ | top-1 との差 [95% CI] |
|---|---|---:|---:|---:|---:|---:|
| `hybrid-0.5` | top-1 | 0.159 | 0.118 | 0.111 | 1.00 | — |
| `hybrid-0.5` | `GreedyConstrainedSetSelector`（tool ≤ 3） | 0.142 | 0.163 | 0.002 | 3.00 | — |
| `hybrid-0.5` | 首位比 0.9 以上（最大 5） | 0.178 | 0.160 | 0.078 | 2.73 | +0.018 [0.008, 0.029] |
| `hybrid-0.5` | oracle top-k（正解件数を知っている） | 0.179 | 0.166 | 0.125 | 1.80 | +0.020 [0.013, 0.028] |
| `llm:hybrid-0.5` | top-1 | 0.176 | 0.139 | 0.119 | 1.00 | — |
| `llm:hybrid-0.5` | top-3 | 0.154 | 0.173 | 0.002 | 3.00 | — |
| `llm:hybrid-0.5` | **`CoverageSetSelector`（min_gain 0.1）** | 0.181 | 0.158 | 0.101 | 1.64 | +0.004 [−0.005, 0.014] |
| `llm:hybrid-0.5` | 首位比 0.9 以上（最大 5） | 0.189 | 0.169 | 0.084 | 2.74 | +0.013 [0.002, 0.024] |
| `llm:hybrid-0.5` | `CoverageSetSelector(include_within=0.95)` ※ | 0.189 | 0.171 | 0.082 | 3.21 | +0.013 [0.001, 0.024] |
| `llm:hybrid-0.5` | oracle top-k | 0.194 | 0.181 | 0.134 | 1.80 | +0.017 [0.010, 0.024] |
| `llm!:hybrid-0.5` | **`LLMSetSelector`（上位 20 件）** | **0.243** | **0.258** | 0.085 | 4.05 | **+0.067 [0.049, 0.086]** |

`min_gain` と相対しきい値は dev で選びました（dev F1: 被覆型 0.174〜0.175 で 0.02〜0.1 が同点、首位比 0.9 が 0.182）。※ の行は同じ設定の別実行 [`results/toolret-near-ties.json`](results/toolret-near-ties.json) で、`include_within` は 0.85 / 0.9 / 0.95 のうち dev F1 が最良（0.187）だった 0.95 です。`LLMSetSelector` は 3 件で応答を再生できず（1 件はモデルの安全機構がクエリの内容を拒否）、その 3 件は棄権として採点しています。

### 結果の読み方

- **大規模カタログでは hybrid の意味重みは 0.5 が最良で、0.9 は転移しません**。120 シナリオの Skill コーパスで最良だった 0.9 は、44k ツールでは macro nDCG@10 0.220 と 0.5（0.256）に大きく劣りました。ライブラリ既定の 0.5 が、作者の書いていないラベルで最良です。RRF 融合も 0.5 の hybrid を下回りました。
- **LLM 分解は第1層を有意に改善します**が、改善幅は 1〜2 ポイントです（nDCG@10 +0.019、C@10 +0.012）。下位タスクごとの最良候補が上位に入るためで、融合は blend が RRF より良く（RRF は C@100 を上げる一方 nDCG@10 を下げる）、規則ベースの節分解は有意差がありませんでした（dev では −0.008）。規則ベースは単一の要求も文や接続語で区切ってしまうためで、分解の利得は分解の精度で決まります（ADR 0012）。
- **LLM 再ランクを重ねると最も伸びます**（nDCG@10 +0.043）。候補の記述を読んで比べる処理は、埋め込みと BM25 の合成スコアより正確です。
- **集合選択の主な改善は順位付けから来ています**。分解前の top-1（0.159）から分解後の被覆型（0.181）までの +0.022 のうち、+0.017 は分解後の top-1 で既に得られ、この標本では被覆型の上積み（+0.004）は有意ではありません（test 全件では +0.012 で有意。下の節）。被覆型は集合が小さく Exact が高い（精度寄り）一方、ToolRet の正解には同じ API の複数エンドポイントのような近い候補が並ぶため、首位比の相対しきい値（再現率寄り）が F1 で上回りました。被覆型の価値は、下位タスクや種別ごとに 1 つずつ選び、依存閉包・競合・権限の制約を保つ点にあります（4 種混合の集合選択ベンチマークでは greedy と同じ Set F1 0.609）。近い候補もモデルに渡したい場合は `include_within=0.95` で相対しきい値と同じ F1（0.189）になります。
- **固定の top-k と既定の greedy（tool ≤ 3）は top-1 より悪い**（0.142〜0.154）。ToolRet の正解集合の平均は 1.8 件で、3 件固定は精度を落とします。
- **1 回余分にモデルを呼べるなら `LLMSetSelector` が最良です**（F1 0.243、複数ツール F1 0.258、top-1 比 +0.067）。リポジトリ内の 28 シナリオ（宣言制約付きの合成コーパス）ではソルバーが LLM に勝ちましたが、ToolRet には宣言制約がなく、記述の意味を読む判断が効きます。Kernel はどの Selector の出力にも依存閉包・競合・権限の制約をかけるので、関連性の判断を LLM に、制約をソルバーに任せる組み合わせ（ADR 0005）と両立します。集合は大きめ（平均 4.05 件）です。
- **限界**: 1,689 件の標本（サブセットごとに最大 60 件）での評価で、埋め込みは小型の MiniLM-L6 だけです。大型の埋め込みモデル、ToolRet の instruction 付き設定、論文の公表値との直接比較（この環境では論文を取得できなかった）は未実施です。LLM 段の応答はキャッシュに依存し、モデル更新で変わります。

#### 探索段階で試し、採用しなかったもの

dev 分割または開発中のオフライン分析で、次はいずれも改善しませんでした（数値は ADR 0012）。最良スコアの max 融合、下位タスク重みの固定的な引き上げ（英語で利得が消える）、ファセットごとの関連度の正規化、被覆型への近接同点の追加、候補の所属確率を較正して期待 F1 を最大化する集合サイズ、入出力名の一致による前提ツールの補完（データフロー補完）。


### test 分割の全件（3,920 クエリ）での確認

標本は大きなサブセットを 60 件に間引いています。test 分割の全件（3,920 クエリ、うち複数ツール 1,729 件）を分解してから同じ設定で測り直しました（[`results/toolret-test-full.json`](results/toolret-test-full.json)、`--per-subset 0 --split test`）。LLM 再ランクと `LLMSetSelector` は呼び出し数が多いため、この全件評価には含めていません。

| 構成 | nDCG@10 | C@10 | C@100 | 複数ツール C@10 | nDCG@10 の差 [95% CI] | C@10 の差 [95% CI] |
|---|---:|---:|---:|---:|---:|---:|
| `lexical` | 0.200 | 0.192 | 0.321 | 0.113 | −0.061 [−0.069, −0.055] | −0.068 [−0.078, −0.058] |
| `hybrid-0.5`（基準） | 0.245 | 0.234 | 0.397 | 0.161 | — | — |
| `llm:hybrid-0.5` | **0.267** | **0.249** | **0.408** | **0.179** | **+0.014 [0.011, 0.018]** | **+0.013 [0.007, 0.018]** |

| Retriever | 選択 | Set F1 | 複数ツール F1 | Exact | 平均サイズ | top-1 との差 [95% CI] |
|---|---|---:|---:|---:|---:|---:|
| `hybrid-0.5` | top-1 | 0.199 | 0.135 | 0.140 | 1.00 | — |
| `hybrid-0.5` | 首位比 0.9 以上（最大 5） | 0.222 | 0.182 | 0.100 | 2.71 | +0.023 [0.017, 0.029] |
| `llm:hybrid-0.5` | top-1 | 0.208 | 0.144 | 0.144 | 1.00 | — |
| `llm:hybrid-0.5` | top-3 / `GreedyConstrainedSetSelector`（tool ≤ 3） | 0.192 | 0.201 | 0.002 | 3.00 | — |
| `llm:hybrid-0.5` | `CoverageSetSelector` | 0.219 | 0.178 | 0.139 | 1.57 | +0.012 [0.006, 0.017] |
| `llm:hybrid-0.5` | 首位比 0.9 以上（最大 5） | 0.226 | 0.189 | 0.098 | 2.74 | +0.018 [0.012, 0.024] |
| `llm:hybrid-0.5` | **`CoverageSetSelector(include_within=0.95)`** | **0.229** | **0.192** | 0.112 | 3.14 | **+0.021 [0.015, 0.027]** |
| `llm:hybrid-0.5` | oracle top-k | 0.234 | 0.204 | 0.163 | 1.76 | +0.026 [0.022, 0.030] |

- 第1層の改善（分解で nDCG@10 +0.014）は全件でも再現し、区間は狭くなりました。macro nDCG@10 は標本の test と全件でほぼ同じです（hybrid 0.243 / 0.245）。
- **被覆型の上積みは全件では有意です**（top-1 比 +0.012）。標本 856 件では +0.004 で区間が 0 を含んでいたので、効果は小さく、検出に件数が要る大きさです。`include_within=0.95` を加えると相対しきい値を上回る 0.229 になり、正解件数を知っている oracle（0.234）との差は 0.005 です。
- 分解されたクエリ 1,900 件の既知語率は平均 0.93 で、英語のゴールでは割引がほとんど効かないことも全件で確認できます。

### 埋め込みモデルとクエリ側の指示文

検索ベンチマーク（MTEB）で MiniLM-L6 より強い検索特化モデル **Snowflake Arctic-Embed-S**（33M パラメータ、384 次元）に替えると第1層が上がるか、同じ 1,689 クエリで測りました。Arctic-Embed は非対称なモデルで、クエリ側にだけ指示文（`Represent this sentence for searching relevant passages: `）を付けて学習されています。`EmbeddingProvider.embed_queries()` で文書とクエリを別々に埋め込み、指示文の有無も比べています（`--query-prefix`）。

```bash
python3 benchmarks/run_toolret_benchmark.py --per-subset 60 --retrievers hybrid-0.5,dense --records /tmp/minilm.json
python3 benchmarks/run_toolret_benchmark.py --per-subset 60 --retrievers hybrid-0.5,dense \
    --embed-model snowflake/snowflake-arctic-embed-s \
    --query-prefix "Represent this sentence for searching relevant passages: " --records /tmp/arctic.json
python3 benchmarks/compare_toolret_records.py minilm=/tmp/minilm.json arctic-s=/tmp/arctic.json --output /tmp/cmp.json
```

結果は [`results/toolret-arctic-s.json`](results/toolret-arctic-s.json)、[`results/toolret-arctic-s-no-instruction.json`](results/toolret-arctic-s-no-instruction.json)、対応のある差は [`results/toolret-embeddings.json`](results/toolret-embeddings.json)（MiniLM との差）と [`results/toolret-query-instruction.json`](results/toolret-query-instruction.json)（指示文の有無の差）です。MiniLM-L6 の行は [`results/toolret.json`](results/toolret.json) と同じ値です。差は 1,689 クエリの micro 平均の差と 95% ブートストラップ区間です。

| 埋め込み | hybrid-0.5 macro nDCG@10 | hybrid-0.5 macro C@10 | dense macro nDCG@10 | dense macro C@10 | MiniLM との差（dense nDCG@10） |
|---|---:|---:|---:|---:|---:|
| **MiniLM-L6**（既定） | **0.256** | **0.247** | **0.205** | **0.199** | — |
| Arctic-Embed-S（指示文あり） | 0.241 | 0.221 | 0.178 | 0.163 | −0.026 [−0.037, −0.016] |
| Arctic-Embed-S（指示文なし） | 0.229 | 0.214 | 0.110 | 0.107 | −0.091 [−0.103, −0.078] |

- **MTEB で強いモデルが ToolRet で強いとは限りません**。Arctic-Embed-S は hybrid でも dense でも MiniLM に有意に劣りました（hybrid nDCG@10 −0.014 [−0.022, −0.007]、C@100 −0.045 [−0.060, −0.031]）。ToolRet 論文の「検索モデルはツール検索が苦手」という結論と同じ向きで、既定の MiniLM-L6 は変えません。
- **非対称モデルにはクエリ側の指示文が必須です**。指示文を外すと dense の nDCG@10 が 0.065 [0.056, 0.074]、C@100 が 0.098 [0.082, 0.114] 下がります。`embed()` しか無かった以前の `EmbeddingProvider` では、この種のモデルを指示文なしの状態でしか使えませんでした。
- CPU 4 コアでの 44,453 件の文書埋め込みは、MiniLM-L6 が約 40 分、Arctic-Embed-S が約 90 分、bge-small-en-v1.5 が約 4 時間、bge-base-en-v1.5 が 10 時間以上でした（他の処理と CPU を共有した状態の見積もり）。大型モデルはこの環境では測っていません。

### 日本語のゴールで英語のカタログから選ぶ

ToolRet のツール記述は英語です。test 分割から各サブセット 6 件（206 件）を Claude Sonnet で自然な日本語に訳し（`run_toolret_llm_stages.py --stage translate-ja`）、同じ 206 件を英語のまま検索した場合と比べました（[`results/toolret-ja.json`](results/toolret-ja.json)、[`results/toolret-ja-english-baseline.json`](results/toolret-ja-english-baseline.json)）。`!` は既知語率による割引なし、`@1` は下位タスク重み 1 です。

| 構成 | 英語 nDCG@10 | 英語 C@10 | 日本語 nDCG@10 | 日本語 C@10 | 日本語 C@100 | 日本語 top-1 F1 | 日本語 被覆 F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `lexical` | 0.217 | 0.219 | 0.013 | 0.019 | 0.071 | 0.010 | 0.010 |
| `hybrid-0.5` | 0.252 | 0.252 | 0.029 | 0.029 | 0.057 | 0.024 | 0.024 |
| `llm!:lexical` | 0.233 | 0.233 | 0.072 | 0.076 | 0.214 | 0.026 | 0.057 |
| `llm:lexical` | 0.230 | 0.233 | 0.091 | 0.095 | 0.205 | 0.041 | 0.061 |
| `llm!:hybrid-0.5` | 0.268 | 0.252 | 0.057 | 0.043 | 0.138 | 0.042 | 0.067 |
| `llm@1!:hybrid-0.5` | 0.267 | 0.262 | 0.134 | 0.129 | 0.248 | 0.076 | 0.081 |
| **`llm:hybrid-0.5`（既定）** | **0.268** | 0.252 | **0.134** | 0.119 | 0.243 | **0.082** | 0.080 |

- **字句検索も英語専用の埋め込みも、日本語のゴールではほぼ機能しません**（nDCG@10 0.013 / 0.029）。日本語の CJK バイグラムは英語のカタログに存在せず、残る数少ない既知語（人名・数値・固有名）が関連度の基準を独占するためです。
- **LLM 分解は翻訳を兼ねます**。`LLMQueryDecomposer` は英語の下位タスクを返すので、下位タスクの検索は英語と同じように働きます。ただし既定の重み 0.25 のままでは日本語のゴール自身の（雑音の多い）リストが順位を支配し、0.057 に留まります。
- **既知語率による割引**（ゴールの語のうちカタログの索引にある割合でゴール側を重み付けする）で、重みを手で 1 にしたのと同じ 0.134 に自動で達します（hybrid 比 +0.106、95% CI [0.076, 0.136]）。分解された 108 件の既知語率は、英語が平均 0.93、日本語が 0.31 で（各 JSON の `goal_weight_mean`）、英語では結果が変わりません（0.268 → 0.268）。
- 英語のまま検索した場合（0.268）との差はまだ大きく、英語のゴール自体が持つ文脈（固有名詞と説明語の組み合わせ）は下位タスクだけでは補えません。多言語の埋め込みモデルを使う構成は未測定です。

## ToolRet-SAE: 選択・エスカレート・棄権

ToolRet のクエリにはすべて答えがあり、ツールもすべて使えるので、制約つき集合選択のもう 2 つの出力、**棄権**（カタログに該当なし）と**エスカレート**（権限の無いツールでしかできない）を測れません。`run_toolret_sae.py` は上の 1,689 クエリの標本から、クエリごとに 3 つの変種を作ります。

- **S（選択）**: カタログそのまま。正解ツールの権限は付与する。
- **E（エスカレート）**: カタログそのまま。正解ツールのスコープだけを付与しない。
- **A（棄権）**: 正解ツールをカタログから削除する。

**権限**: 全ツールが不透明なスコープを 1 つ要求します（`scope.<n>`、n はツール ID の SHA-1 mod 40）。各変種は、正解が使わないスコープの 70% をクエリ ID の乱数で付与し、S と A では正解のスコープも付与します。どの変種でも妨害候補の約 3 割が権限で阻まれるので、「阻まれた候補がある」こと自体は E の手がかりになりません。権限は検索の後に付けるので、S と E の順位は同一、A は S から正解を除いたものです（選択段だけを比べるため。ライブラリの複合スコアなら阻まれた候補の順位がわずかに下がります）。

**正解の状態**: 全手法が同じ上位 20 候補から選ぶので、評価対象に使っていないアノテータモデル（Claude Opus）が、正解ツールと候補を読み、正解ツールごとに「依頼に必要か」と「どの候補が代わりになるか」を判定します（IR の pooling と同じ考え方）。A は「必要な正解ツールのどれかに、A の候補内で代替が無い」とき棄権が正解、E は「必要な正解ツールのどれかに、許可された代替が無い」ときエスカレートが正解です。そうでない変種は除外して数えます。S は、必要な正解ツールを全部（本体か代替で）含む集合を選んだときだけ正答とします。正解を候補に入れた条件（S+ / E+、正解は検索での順位の位置に入れる）で、検索と選択を分けて測ります。

```bash
python3 benchmarks/run_toolret_sae.py --stage pools                                # 候補（llm:hybrid-0.5 の上位 100）
python3 benchmarks/run_toolret_sae.py --stage label --workers 8                    # Opus による代替・必要性の判定
python3 benchmarks/run_toolret_sae.py --stage agree --agree-queries 200            # 第 2 アノテータ（Sonnet）
python3 benchmarks/run_toolret_sae.py --stage methods --split test                 # LLM 手法（Sonnet）
python3 benchmarks/run_toolret_sae.py --stage methods --split test --limit 300 --oracle
python3 benchmarks/run_toolret_sae.py --stage methods --split dev --limit 200 --method req-cover
python3 benchmarks/run_toolret_sae.py --stage score
```

結果は [`results/toolret-sae.json`](results/toolret-sae.json)。LLM の応答は `benchmarks/cache/` に保存し、採点時は再生します。モデルの安全機構が拒否した呼び出し（保存した応答のうち `LLMSetSelector` 15 件、`RequirementCoverageSelector` 4 件）は、拒否として保存し棄権として採点します。

**データ**: 正解ツール 3,090 件のうち 90.3% が「必要」、44.1% に上位 20 候補内の代替がありました。ToolRet の正解だけで採点する標準指標は、重複の多いカタログでは選択の正しさを過小評価しうる値です。test 分割の有効な変種は S 856、E 546、A 472 件です。上位 20 候補に必要な正解か代替が揃う（reachable）S は 478 件でした。第 2 アノテータとの一致度は、代替判定（6,960 組）が κ=0.80、必要性が κ=0.73、変種の有効性が κ=0.78 です。

**事前登録**: 結果を見る前に、`RequirementCoverageSelector` の採用基準を 4 つ決めました（主指標は S / E / A の正答率のマクロ平均）。

1. dev で調整した最良の規則を上回り、CI が 0 を含まない。
2. `LLMSetSelector` に劣らない（差の CI 下限 > −0.02）。
3. S での不要な escalate が `LLMSetSelector` + 0.02 以下。
4. 1 回の選択あたりの LLM 呼び出しが `LLMSetSelector` と同じ 1 回。

`per_requirement` は dev の S Set F1 で選ぶ、とも決めました。

| test（856 クエリ） | 関連度の下限 | マクロ正答率 | S 正答 | E 正答 | A 正答 | S Set F1 | S 不要 escalate | E 誤選択 | A 誤選択 | 平均サイズ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 首位の許可候補（常に選ぶ） | 0 | 0.080 | 0.240 | 0.000 | 0.000 | 0.195 | 0.000 | 1.000 | 1.000 | 1.00 |
| 首位（阻まれていれば escalate） | 0.75（dev） | 0.343 | 0.015 | 0.064 | 0.949 | 0.016 | 0.020 | 0.028 | 0.025 | 1.00 |
| `GreedyConstrainedSetSelector` | 0.75（dev） | 0.344 | 0.020 | 0.064 | 0.949 | 0.018 | 0.020 | 0.028 | 0.025 | 1.83 |
| `GreedyConstrainedSetSelector` | 0 | 0.288 | 0.332 | 0.533 | 0.000 | 0.120 | 0.242 | 0.467 | 0.682 | 5.00 |
| `CoverageSetSelector` | 0.75（dev） | 0.344 | 0.018 | 0.066 | 0.949 | 0.018 | 0.021 | 0.026 | 0.025 | 1.21 |
| `CoverageSetSelector` | 0 | 0.267 | 0.233 | 0.568 | 0.000 | 0.176 | 0.272 | 0.432 | 0.634 | 1.46 |
| `LLMSetSelector`（Sonnet、1 回） | — | 0.298 | **0.505** | 0.222 | 0.167 | **0.255** | **0.023** | 0.678 | 0.765 | 3.54 |
| `RequirementCoverageSelector`（best） | — | 0.437 | 0.431 | **0.392** | **0.487** | 0.245 | 0.060 | **0.300** | **0.411** | 1.33 |
| **`RequirementCoverageSelector`（all、dev で選択）** | — | **0.447** | 0.463 | **0.392** | **0.487** | 0.242 | 0.060 | **0.300** | **0.411** | 2.85 |

主指標の差（クエリを再標本化した対応のあるブートストラップ、95%）:

| 比較 | マクロ | S | E | A |
|---|---:|---:|---:|---:|
| `RequirementCoverageSelector`（all） − greedy（下限 0.75） | **+0.103 [0.077, 0.129]** | +0.443 [0.409, 0.477] | +0.328 [0.282, 0.373] | −0.462 [−0.512, −0.415] |
| `RequirementCoverageSelector`（all） − `LLMSetSelector` | **+0.149 [0.130, 0.169]** | −0.042 [−0.057, −0.028] | +0.170 [0.133, 0.209] | +0.320 [0.273, 0.367] |
| `LLMSetSelector` − greedy（下限 0.75） | −0.047 [−0.070, −0.023] | +0.485 [0.451, 0.520] | +0.158 [0.117, 0.197] | −0.782 [−0.821, −0.744] |

正解を候補に入れた条件（test の 445 クエリ、S+ 445・E+ 255 変種）:

| | S+ 十分な集合 | S+ Set F1 | E+ escalate | E+ 誤選択 |
|---|---:|---:|---:|---:|
| `LLMSetSelector` | **0.928** | 0.585 | 0.475 | 0.502 |
| `RequirementCoverageSelector`（all） | 0.838 | 0.581 | **0.796** | **0.165** |

**結果の読み方**

- **関連度の下限では状態を決められません**。dev でマクロ正答率を最大化した下限 0.75 は、ほぼ常に棄権する解（A 正答 0.95、S 正答 0.02）で、0.344 は「常に棄権」（0.333）とほぼ同じです。下限なしでは A で一度も棄権しません。上の「棄権は Coverage と Selective Accuracy のトレードオフ」の観測が、作者以外のラベルでも再現しました。
- **LLM に集合と状態をまとめて決めさせると、選んでしまいます**。`LLMSetSelector` は S では最良ですが、A の 76%、E の 68% で何かを選び、調整済みの下限にもマクロで劣りました（−0.047）。正解を候補に入れても、E+ の半分で権限の無い正解の代わりに別のツールを選びます。リポジトリ内の宣言制約つき合成ベンチマーク（abstain / escalate 精度 100%）とは逆の結果です。
- **状態を宣言制約からソルバーが決めると、マクロ正答率が最も高くなります**（greedy 比 +0.103、`LLMSetSelector` 比 +0.149）。LLM には「要求ごとに満たす候補」だけを判定させ、権限は見せません。E+ の escalate は 0.475 → 0.796 に上がりました。
- **事前登録の基準 3 は満たしませんでした**。S での不要な escalate が 0.060 で、上限（0.023 + 0.02）を超えたため、推奨・既定化はしません（ADR 0013）。誤りを分析すると、S の escalate 51 件中 42 件は候補 20 件に「許可された正解・代替」が無く権限の無い類似ツールしか無い状況で、S の誤った棄権 184 件中 166 件も候補に必要なツールが無い状況でした。主な原因は検索の上限（上位 20 件に正解が揃うのは標本全体で 32%、`gold_in_pool`）です。件数は各手法の `diagnostics` にあります。
- **残る本質的な誤りは能力判定の甘さです**。A で何かを選んだ 194 件のうち、ラベル上の代替を含むのは 40 件でした（`LLMSetSelector` は 361 件中 118 件）。
- **限界**: 正解の状態は LLM アノテータの判定で、人のラベルではありません。手法も同系統の Sonnet なので、モデル間の相関が提案手法を有利にしている可能性は残ります。権限は意味を持たないハッシュのスコープです。LLM の応答はキャッシュに依存し、再実行で変わります。

### held-out での再評価（2026-11-27、#45）と、ラベルの検証（#48）

前回の test 分割は一度評価に使ったので、ToolRet の未使用クエリから held-out を作り、手法を直してから一度だけ評価しました。数値は [`results/toolret-sae-heldout.json`](results/toolret-sae-heldout.json) によります。

```bash
python3 benchmarks/run_toolret_sae.py --stage heldout                     # held-out の ID を固定（済み）
python3 benchmarks/run_toolret_llm_stages.py --stage decompose --model haiku --split heldout --sample 400
python3 benchmarks/run_toolret_sae.py --stage pools --stage label --split heldout --sample 400
python3 benchmarks/run_toolret_sae.py --stage agree --agree-queries 100
python3 benchmarks/run_toolret_sae.py --stage methods --split heldout --sample 400 --method llm-set --method req-cover-strict
python3 benchmarks/run_toolret_sae.py --stage score --stage export-labels --stage substitutes --method llm-set --method req-cover-strict
```

**前回との違い**（このため、上の test の表とは直接比べられません）:

- ラベルは Claude Sonnet、手法と第 2 アノテータは Claude Haiku です（CLI 呼び出しが Sonnet と Haiku に限定されたため。前回は Opus / Sonnet / Sonnet）。
- ラベルと変種の有効性は上位 40 候補で判定します（前回は 20）。手法が見る候補は 20 のままです。
- held-out は [`toolret_sae_heldout_ids.json`](toolret_sae_heldout_ids.json) の 852 件（標本に含まれないクエリ、18 サブセット）のうち、ID の SHA-1 順の先頭 400 件です。有効な変種は S 400、E 205、A 167 件でした。
- 手法は、判定プロンプトを厳しくした `RequirementCoverageSelector(judge="strict")` です。dev で 4 つの設定から事前の規則で選び、設定・採用基準・held-out を、held-out のラベルを付ける前に ADR 0013 に記録しました。escalate の前に次点の許可候補を判定する経路（`extra_candidates`）は、dev で主指標を下げたので採りませんでした。

| held-out（400 クエリ） | 関連度の下限 | マクロ正答率 | S 正答 | E 正答 | A 正答 | S Set F1 | S 不要 escalate | E 誤選択 | A 誤選択 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `GreedyConstrainedSetSelector` | 0.55（dev） | 0.386 | 0.160 | 0.268 | 0.731 | 0.108 | 0.068 | 0.161 | 0.174 |
| `CoverageSetSelector` | 0.55（dev） | 0.379 | 0.138 | 0.268 | 0.731 | 0.122 | 0.070 | 0.161 | 0.174 |
| `LLMSetSelector`（Haiku、1 回） | — | 0.376 | **0.600** | 0.283 | 0.246 | **0.300** | **0.020** | 0.576 | 0.683 |
| **`RequirementCoverageSelector`（strict、Haiku、1 回）** | — | **0.552** | 0.468 | **0.439** | **0.749** | 0.269 | 0.070 | **0.112** | **0.174** |

事前登録した採用基準の結果:

1. dev で最良の規則（greedy、下限 0.55）を上回り、CI が 0 を含まない: **満たす**（+0.165 [0.123, 0.211]）。
2. `LLMSetSelector` に劣らない: **満たす**（+0.176 [0.143, 0.211]）。
3. S での不要な escalate が `LLMSetSelector` + 0.02 以下: **満たさない**（0.070、上限は 0.020 + 0.02 = 0.040）。
4. 1 回の選択あたりの LLM 呼び出しが最大 2 回: **満たす**（1 回）。

基準 3 は前回と同じく未達なので、推奨・既定化はしません（ADR 0013 は Proposed のまま）。

- 主指標の差は前回（+0.149）と同程度で、モデルと分割を替えても再現しました。E と A で選んでしまう誤りが `LLMSetSelector` より大幅に少ないことが効いています。
- S の不要な escalate 28 件のうち 18 件は、候補 20 件に許可された正解・代替が無い状況でした（`diagnostics`）。同じ下限の greedy も 0.068 で、`LLMSetSelector` だけが 0.020 と低い値です。`LLMSetSelector` は E の 58% で権限の無い正解の代わりに別の候補を選ぶので、S で escalate が少ないことと E で escalate できないことは同じ性質の表と裏です。
- S の正答は `LLMSetSelector` より 0.133 低く、誤った棄権が多い（0.308）ことが原因です。123 件中 90 件は候補に必要なツールが無い状況でした。
- `per_requirement="all"` は 0.561 でしたが、dev の規則で選んだのは best なので、判定には best を使いました。

**ラベルの検証**（#48。人による検証は行っていません）:

- 第 2 アノテータ（Haiku、held-out の 100 クエリ）との一致度は、代替判定（7,520 組）が κ=0.80、必要性が κ=0.79、変種の有効性が κ=0.88 でした。どちらも Claude 系のモデルで、手法も Haiku なので、同系統どうしの相関が結果を有利にしている可能性は排除できません。別系統のモデルとの一致度は未測定です。
- ラベルは [`results/toolret-sae-heldout-labels.json`](results/toolret-sae-heldout-labels.json) に置きました（dev 833、test 856、held-out 400 件）。中身は ToolRet のクエリ ID とツール ID、必要性と代替の判定だけで、クエリやツールの本文は含みません。

**代替ツールが ToolRet の標準指標に与える影響**（[`results/toolret-substitutes.json`](results/toolret-substitutes.json)、ラベルのある 2,089 クエリ、検索は `llm:hybrid-0.5`、macro）:

| 採点 | nDCG@10 | Recall@10 | Completeness@10 |
|---|---:|---:|---:|
| 正解ツールだけ（ToolRet の標準） | 0.266 | 0.348 | 0.262 |
| 正解または代替 | 0.437 | 0.526 | 0.397 |
| 必要な正解または代替 | 0.452 | 0.554 | 0.446 |

- 正解ツール 3,817 件のうち 51.9% に上位 40 候補内の代替があり、「必要」と判定されたのは 88.0% でした。
- 代替を認めると nDCG@10 は 0.266 から 0.437 に上がります。重複の多いカタログでは、正解だけで採点する標準指標が検索の正しさを大きく過小評価していることになります。複数ツールのクエリ（911 件）の Completeness@10 は 0.108 から、必要な正解または代替で 0.300 になります。
- 代替の判定は LLM によるもので、上位 40 候補の中だけです。値は上限の目安として読んでください。

## 注意

`resources/skills` は出典を `resources/skills/SOURCES.md` に記録した外部リポジトリのコピーで、ベンチマーク・検証専用です。再配布ライセンスの整理が完了するまで、このコーパスを成果物として再配布しないでください。この方針のため、`.gitignore` で git 管理から外し、`MANIFEST.in` でも sdist から除外しています。
