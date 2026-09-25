# 0010. 再開時は選択済み実行 Snapshot を復元する

- 状態: Accepted
- 日付: 2026-09-25
- 根拠: `marmo_core/execution_snapshot.py`、`marmo_core/kernel.py`

## 文脈

HITL で task を一時停止した後にカタログ、Retriever、Selector が変わると、再開時に別の
Resource が選ばれる可能性があった。承認済みの操作と実際の実行先を一致させる必要がある。

## 判断

- 選択が確定した時点で resource identity、宣言内容の fingerprint、スコア、選択理由を
  `snapshot` state event に追記する。
- 再開時は保存した選択結果を復元し、retrieval と selection を再実行しない。権限不足で
  selection が escalate した場合は、Resource set 未確定なので権限付与後に選択する。
- activation 後に compiled context の fingerprint も保存し、選択 Resource または context が
  変わった場合は task を失敗で終端する。
- memory / skill の本文は policy が activation を許可した直後に hash を追記する。後続の
  activation gate で一時停止して再開する際、本文が変わっていれば task を失敗で終端する。
- snapshot がない既存 task でも、activation / execution を通過した履歴があれば現行カタログで
  再選択せず失敗で終端する。selection 段階での pause は set 未確定のため再選択を許す。
- Resource の実績統計 `stats` は fingerprint から除き、運用統計の更新で task が無効に
  ならないようにする。

## 影響

カタログや、読み込み済み memory / skill の本文が変わった状態で一時停止 task を再開すると、
変更が実行を止める。元のカタログと同じ選択・コンパイル結果で再開する必要がある。選択済みの実行可能関数の
内部コードや外部サービスの状態までは Snapshot に保存しない。snapshot 導入前に activation /
execution で一時停止した task は対象を復元できず、拒否される。

## 代替案

毎回再検索・再選択する方式は、承認した対象を変え得るため採らない。Resource 定義全体を
state に複製する方式は、メモリや設定などの内容を重複保存するので採らない。
