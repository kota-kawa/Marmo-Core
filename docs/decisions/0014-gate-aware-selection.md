# 0014. Selector はゲートが必ず拒否する候補を選ばず、escalate の理由にもしない（opt-in）

[English](0014-gate-aware-selection.en.md)

- 状態: Accepted（opt-in。既定化は見送り）
- 日付: 2026-11-26
- 根拠: `marmo_core/policy.py` の `static_denials`、`marmo_core/selector.py` の `_gate_admissible`、
  `benchmarks/run_forgery_benchmark.py`、`benchmarks/results/forgery.json`、
  `benchmarks/README.md` の「偽装メタデータの継続計測」節

## 文脈

責務分割は「検索は順位、選択は制約、ゲートは実行可否」である。選択が見る宣言は権限だけで、
信頼度・副作用・隔離レベルは activation gate だけが見ていた。偽装メタデータの計測（#38、#46）で、
このずれが次の 2 つを起こすと分かった。

1. ゲートが拒否する資源を Selector が選び、正規の資源の枠を取る。権限だけを偽装した Tool は
   選ばれてから拒否され、gold Tool は 37% のケースでモデルに渡らなくなった。
2. 説明文にタスクの語を詰め込み、権限を正直に宣言した資源が、「権限だけで阻まれた上位の単位」
   として escalate を起こす。人に権限の付与を求めるが、付与してもその資源はゲートを通らない。

権限フィルタを検索に押し下げると escalate 能力が壊れた前例がある（Policy アブレーション、100% → 50%）。

## 判断

- ゲートの拒否理由のうち、権限の付与や人の承認で解消しないものを `policy.static_denials` に
  まとめる。対象は、許可されない信頼度と副作用、使えない・最低水準に満たない隔離レベル。
  `PolicyGateway.evaluate` も同じ判定を使うので、選択とゲートがずれない。
- `SelectionContext.policy` にゲートの方針を渡すと、rule-based・greedy・beam・分枝限定・被覆型・top-k の
  各 Selector は、該当する候補を単位を作る前に外す。選ばず、依存先としても数えず、escalate の
  理由にもしない。外した候補は選択理由に残す。
- 権限不足と、人の承認を待つ副作用は対象にしない。従来どおり escalate する。検索の順位は変えない。
- `Kernel(gate_aware_selection=True)` で Kernel が自分の方針を渡す。既定はオフにする。

## 影響

実装前に決めた条件（コミット 5ea1990b）は、効果（一部偽装の gold Tool 喪失と、正直な宣言での
状態の変化がどちらも下がる）と、既存ベンチマークの悪化なしだった。

- 効果は満たした。greedy の Tool で、一部偽装の gold Tool 喪失は 0.374 → 0.170、正直な宣言での
  状態の変化は 0.307 → 0.170。`tracked` の集計で悪化した指標は無い。細かい区分
  （`by_kind_content_attack`）では、信頼度を偽装した stuffed の 6 区分で状態の変化が 50 変種中
  1 件ずつ増えた。
- 悪化が 1 件あった。evidence の `dev-escalate` は、通知 Tool が権限に加えて既定の実行環境に無い
  隔離レベル L3 を要求するため、escalate から abstain に変わる（状態の正答率 0.955 → 0.909）。
  権限を付与してもこの Tool はゲートを通らないので新しい結果のほうが実態に合うが、ラベルは
  escalate であり、条件は事後に変えない。このため既定にはしない。
- 偽装なしの集合選択 28 シナリオの状態の正答率（0.714、rule-based は 0.857）と、evidence で gold Tool が
  モデルに渡る割合（0.929）は変わらない（`forgery.json` の `suites.*.configs.*.clean`）。
- 既定がオフなので、既存の選択結果と公開 API の互換性は変わらない。追加は任意の項目だけである。

`TopKSetSelector` と `RepairingSetSelector` も同じ候補を外す。LLM を使う Selector は `policy` を読まない。
`max_cost` による拒否は対象に入れていない。

## 代替案

- 選ばないだけにして、escalate の理由には残す: 実装前に決めた 2 案の片方として試した。悪化は
  無かったが、正直な宣言での状態の変化が下がらず、効果の条件を満たさなかった（試行の結果は
  コミットしていない）。
- 検索や候補プールでゲートの拒否をすべて落とす: 権限不足まで落とすと escalate できなくなる。
- 既定にする: 上の 1 件が解消するか、ラベルを見直す判断があれば再検討する。
