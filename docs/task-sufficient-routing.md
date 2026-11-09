# 要求充足を扱う Object Routing（研究用 opt-in）

Memory・Skill・Tool・Agent の共通登録、検索から集合選択への2段構成、Kernel の
活性化・実行ゲートを維持し、要求の充足を明示する研究用 API である。
研究計画と未完了の評価は [Research issue 78](https://github.com/kota-kawa/Object-Routing-Research/issues/78) で管理する。

## 要求と資源契約

`TaskSpec.from_mapping` は `requirements` 内の `all_of` / `one_of` を解釈する。
要求は action、entity_type、target_scope、output_type、mode の型付き記述とする。
5項目の欠落は wildcard とせず unknown とする。
effect（実行）、information（情報提供）、context（手順・文脈）を区別し、
送信を説明する Skill だけで送信処理を実行可能と判定しない。

資源は任意の extras 項目 `routing_contract` に observed / complete、affordances、
context.all_of / context.one_of、call_preconditions、permissions、source_evidence を記録する。
schema_version=1 とこれらの構成要素は明示する。依存や権限が不要なら空の値を宣言し、
未指定を空の宣言として補わない。
出所がない宣言や未対応の形式は unknown であり、権限も能力も自動的には与えない。
出所の記録は、宣言が真実である証明や、悪意ある登録に対する防御ではない。
語彙を固定する場合は TaskSpec と各契約に `vocabulary_version` と SHA-256 の
`vocabulary_hash` を両方指定する。不一致や片側だけの指定は unknown とする。
両側とも省略した場合は語の完全一致だけを使い、公開オントロジーの検証済みとは扱わない。
hash が一致しても、action/entity がその語彙の登録語であるかを照合する処理は未実装である。
`call_preconditions` が残る資源も、実行時の根拠を検証できるまでは unknown とする。

```python
from marmo_core import GoalAwareSetSelector, Kernel, TaskSpec

spec = TaskSpec.from_mapping({
    "requirements": [{
        "action": "send", "entity_type": "message",
        "target_scope": "workspace/team", "output_type": "receipt",
        "mode": "effect",
    }],
})
selector = GoalAwareSetSelector(lambda goal: spec, strategy="exact")
# registry と llm は既存の ResourceRegistry / LLMProvider を用意する。
kernel = Kernel(registry, llm, selector=selector)
```

上の固定 provider は API の例であり、全ての依頼に同じ spec を使う実運用の例ではない。
要求抽出器は利用者の依頼だけから spec を作り、正解資源 ID や評価用の隠れた状態を
見てはならない。自然言語からの自動抽出精度は、本変更で評価済みではない。

## 集合選択

`strategy="greedy"` は要求の被覆増分を用い、`strategy="exact"` はノード上限付き探索を行う。
検索スコアの総和を報酬にせず、要求を満たす集合から権限露出・描画量・費用などを減らす。
共有依存を二度加点しない。`rendered_token_cost` は選択集合全体の描画量を返す callback で、
実モデルの入力課金数を保証する API ではない。最適性は探索が完了した候補範囲だけの性質である。
さらに最適性は設定した callback に対してだけ成立する。既定 proxy を使う場合、
実本文や Tool schema の描画量について最適とは主張しない。
`SelectionContext.context_token_budget` はこの callback の返す量に対するハード制約である。
既定 callback はメタデータ由来の代理値なので、実際の描画に合う callback を渡す必要がある。
このため予算を設定する場合は `rendered_token_cost` の明示を必須とし、省略時は uncertain とする。
Kernel は資源本文に合う callback を自動生成しない。上の最小例は文脈予算を設定していない。

`selected` は観測した契約の下で充足集合を作れるという意味で、タスク成功ではない。
許可された代替があれば権限追加を求めず、権限だけで充足可能になる場合に `escalate` を返す。
候補不足、未知情報、探索打ち切りは理由を付けて `abstain` とする。
Kernel の候補生成も、この opt-in では権限不足だけを理由に下位の代替候補を落とさない。
実際の権限は付与せず、その他の policy deny と活性化・実行ゲートを維持する。
渡された registry は発見可能なカタログと仮定する。発見そのものを禁止する独立した ACL は
現在の API にないため、機密資源は呼び出し元が registry に含めない必要がある。

## 実際に渡す文脈の検査

この Selector は `requires_contract_verification=True` を公開する。
Kernel は（この Selector に限らず）既定 compiler を `ContextCompiler(preserve_dependencies=True)` とし、
metadata と観測した context 依存を閉包単位で格納する。全4種類に適用し、
依存する本文の部分切り捨てを完全な依存として扱わない。
曖昧な版参照、欠落、循環、未知の契約は安全側に除外する。

Kernel は活性化後・コンパイル後にも充足を検査し、同じ ID のまま本文や Tool schema が
書き換わっていないか、活性化済み資源を信頼できる compiler で再描画して比較する。
不足した集合でモデルを呼ばず、失敗と監査記録を返す。snapshot からの再開にも適用する。
同じ ID で別の内容を意図的に出力する custom compiler は、この opt-in では拒否される。
TaskSpec は検索前に一度だけ解決して snapshot に保存する。権限不足による承認待ちでも
再抽出せず、同じ要求の下で再選択する。要求抽出に失敗した場合はモデルを呼ばない。
確定した集合の費用制約は選択時の残額で保存する。途中再開時に実行済み資源の見積りを
もう一度残額と比較しない。各モデル呼び出し・資源実行の予約は現在の残額で別途検査する。

現時点では後段の脱落に対し実行を停止する。代替集合を探索して再コンパイルする一般的な
回復経路、データ受け渡しを含む任意の呼び出し前条件の実行時証明は未完成である。
新しい契約・実行経路を完全に検証するまで研究全体を完了と扱わない。
検索で候補に入らなかった宣言済み依存先を ID で最大128件まで補充する、比較方式共通の
経路も未実装である。現在は候補内に閉包を作れなければ unknown / abstain とする。

既存の Selector と compiler の既定挙動は変えない。モデルの指示遵守、宣言の真偽、
実際のタスク完了、プロバイダの課金トークン上界は別に評価する。
