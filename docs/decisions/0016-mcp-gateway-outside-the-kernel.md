# 0016. MCP ゲートウェイは Kernel の外で同じゲートを通し、人の承認が要る操作は拒否する

[English](0016-mcp-gateway-outside-the-kernel.en.md)

- 状態: Accepted
- 日付: 2026-11-27
- 根拠: `marmo_core/mcp_server.py`、`tests/test_mcp_server.py`、issue #35 の「5. OSS として出す形」

## 文脈

Marmo-Core の検索・集合選択・ゲートを使うには、利用側が `Kernel` を組み込み、モデルの呼び出しも
Kernel に任せる必要があった。自分のモデルとエージェントループを持つホスト（MCP クライアント）は、
選択とゲートだけを使えなかった。MCP クライアントのモデルと会話は Marmo-Core の外にあり、Kernel の
状態を共有しない。

## 判断

- `MCPGatewayServer` を追加し、MCP の tool として `search_tools` と `call_tool` の 2 つだけを公開する。
  カタログの大きさにかかわらず、クライアントに最初に渡る定義は 2 つである。
- Kernel は経由しない。Kernel はモデルを呼ぶ実行ループで、モデルはクライアント側にあるためである。
  代わりに、Kernel と同じ部品を同じ順に通す。`KindBalancedCandidatePool`、`SetSelector`、
  `_enforce_set_constraints`、activation gate、`ToolRuntime.execute`（execution gate、引数の検証、
  `SafetyInspector`、タイムアウト）。
- クライアントは信頼境界の外に置く。`PolicyContext` は起動者が固定し、クライアントからは変えられない。
  `search_tools` がそのセッションで返していない Tool は呼べない。
- この経路には承認者がいない。ゲートが escalate とする操作は、理由を付けて拒否する。事前の承認は、
  起動者が `approved_resources`（CLI は `--approve-resource`）で与える。
- Kernel と同じく、Tool の結果をクライアントに返した後の write / external / irreversible の呼び出しは、
  信頼されない内容の後に提案された操作として扱う。操作単位の承認が要るため、ゲートウェイでは拒否になる。
- Tool の結果は `label_untrusted_content` の区切りに入れ、`max_tool_output_tokens` で切り詰める。
- 対象は Tool だけにする。Memory・Skill・Agent に依存する Tool は公開しない。

## 影響

- 副作用のある Tool は、事前に承認されていても、同じセッションで Tool の結果を一度返した後は呼べない。
  ゲートウェイは読み取り中心のカタログに向く。書き込みを伴う作業は、HITL のある Kernel を使う。
- 再試行、fallback、補償、サーキットブレーカー、タスク予算、呼び出し回数の上限（`max_tool_calls`）、
  状態の保存と再開、Connector、`SecretResolver`、`HitlPolicy` の「常に確認」はゲートウェイに無い。
  1 回の呼び出しは 1 回の試行で、判定と結果は監査ログに残る。
- 依存と競合の制約は 1 回の検索の集合にかける。加えて、セッションで既に返した Tool と競合する Tool は
  返さない。
- `requires_contract_verification` を持つ Selector（`GoalAwareSetSelector`）は受け付けない。TaskSpec の
  抽出とコンパイル後の検査は Kernel だけが行うためである。
- 選択から activation までの手順が、Kernel と `mcp_server.py` の 2 か所になる。ゲートの判定は
  `PolicyGateway` と `ToolRuntime` を共有するのでずれないが、Kernel 側の手順（候補プール、制約の適用）を
  変えるときはゲートウェイも確認する。
- Kernel の既定挙動と既存の公開 API は変わらない。追加は `MCPGatewayServer` と `marmo mcp-serve` である。

## 代替案

- カタログの全 Tool を MCP の tool 一覧にそのまま出す: 全定義がクライアントのコンテキストに入り、選択を
  行わない。
- `Kernel.run_goal` を 1 つの tool として公開する: ゲートウェイ側にもモデルが要り、HITL の一時停止を
  クライアントに返せない。
- escalate を MCP の elicitation でクライアントの利用者に尋ねる: 誰が承認できるか
  （`HitlPolicy.approvers`）の境界が変わるので、別の判断として残す。
- 返した結果を追跡しない: クライアントの会話全体は見えないが、ゲートウェイが返した Tool の結果は確実に
  信頼されない内容である。追跡しないと、Kernel より弱い経路になる。
