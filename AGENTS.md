# Marmo-Core Agent Rules

Marmo-Core は、Object Routing を実装する公開 Python ライブラリである。

## 基本方針

- このリポジトリを実装コードの唯一の正とする。
- `main` は安定版として扱う。
- 研究中の新手法は `research/<method-name>` ブランチで実装する。
- `Object-Routing-Research` へ Marmo-Core 本体をコピーしない。

## 研究用変更

新しい Router、Retriever、Selector などを試す場合：

1. `research/<method-name>` ブランチを作る。
2. 実装する。
3. unit test を追加する。
4. テストを実行する。
5. commit SHA を取得する。
6. `Object-Routing-Research` からその commit を使用して評価する。

実験で有効性を確認できるまでは、原則として `main` にマージしない。

## main へ入れる条件

- 実験上の有効性または必要性が確認されている。
- unit test がある。
- 既存 API を不必要に壊さない。
- 一般利用できる実装になっている。
- 必要なドキュメントが更新されている。

## 最重要ルール

研究速度のために公開ライブラリの安定性を壊さない。一方で、研究用ブランチでは新しい手法を積極的に試してよい。
