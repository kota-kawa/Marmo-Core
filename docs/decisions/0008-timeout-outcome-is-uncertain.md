# 0008. timeout 後の操作結果は不明として扱う

- 状態: Accepted
- 日付: 2026-09-25
- 根拠: `marmo_core/tool_runtime.py`、`marmo_core/recovery.py`

## 文脈

従来の Tool timeout は待機中のスレッドを放棄するだけで、ハンドラは動き続けた。
既定の回復ポリシーは timeout を再試行し、二重の書き込みや送信が起こり得た。

## 判断

- timeout を結果不明の操作として記録し、同じ操作の再試行と代替を自動では行わない。
- import 可能な Python ハンドラ向けに停止可能な process モードを追加する。このモードでは
  import できない callable と JSON 対応でない引数を実行前に拒否する。子プロセス群を
  停止できる POSIX 環境のみで提供し、Windows では明示的に拒否する。
- 既存の thread モードは互換性のため残す。既定値を process に変える際は、利用者の
  callable と Connector の移行経路を用意した別の互換性判断を行う。

## 影響

timeout の標準回復は人間へのエスカレーションとなる。process モードでも、既に外部サービスが
受け付けた副作用は取り消せない。厳格モードの handler は module-level の import 可能な関数を使う。

## 代替案

スレッドを放棄して自動再試行する方式は、同じ副作用を重複して実行する可能性があるため採らない。
