# 0011. Agent は実行 backend を選び、structured task は子 Kernel に委譲する

- 状態: Accepted
- 日付: 2026-09-25
- 根拠: `marmo_core/agent_runtime.py`、`marmo_core/kernel.py`

## 文脈

従来の Agent はローカル Python handler を `ToolRuntime` 経由で実行していた。
Resource 定義では `structured_task` を宣言できたが、activation はこれを拒否し、Kernel の
Agent 委譲深度も常に 1 だった。structured Agent が Tool を使うには、親の全 registry、権限、
費用上限をそのまま与えずに、再開可能な実行経路が必要である。

## 判断

`AgentRuntime` は有効化済み Agent を `AgentExecutionBackend` に渡す。組み込みの `tool_wrap`
backend はローカル handler を実行する。`structured_task` backend は、Agent が宣言した
dependencies の推移閉包だけを registry に持つ子 Kernel task を作る。入力 schema は required
string `goal` を持つ。

子 Kernel は親と同じ LLM、Retriever、Selector、Planner、Policy Gateway、Tool Runtime、State
Store、Audit Log、Recovery Manager、task budget を使う。PolicyContext の権限は Agent の宣言に
縮める。人の承認 request は親へ中継し、deterministic な子 task に応答を戻す。子 Tool の結果は
親 state に記録し、補償処理からも参照できるようにする。入れ子の Agent にも設定済みの
`max_agent_depth` と `max_agent_cost` を適用する。

## 影響

独自 backend を登録して Agent の実行環境を拡張できる。structured task は Tool と Agent を
組み合わせても親の policy と予算の境界を保てる。子 task は個別に永続化されるため、利用者は
`AgentResult.child_task_id` から状態を調べられる。既定の深度は 1 のままであり、Agent の入れ子は
明示的な上限設定が必要になる。子が利用できる Resource は dependency 宣言で決まるため、他の
実行 Resource と同じ基準でレビューする。

## 代替案

- Agent をすべてローカル Python handler に限定する案は、宣言済みの `structured_task` を実行
  できないため採らない。
- 子へ親の全 registry と権限を渡す案は、無関係な Resource と権限を見せるため採らない。
- 子ごとに独立した予算を与える案は、入れ子委譲で親の上限を増幅できるため採らない。
