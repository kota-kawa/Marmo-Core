# 0002. 研究手法は `research/*` ブランチで実装し、評価は commit SHA を固定する

- 状態: Accepted
- 日付: 2026-09-22
- 根拠: 2aa8ff19（PR #14）、`AGENTS.md`、ワークスペース直下の `AGENTS.md`、`benchmarks/_provenance.py`

## 文脈

Marmo-Core は公開ライブラリであると同時に研究対象でもある。研究の速度のために `main` の
安定性を壊さないこと、論文の数値がどの実装で出たかを後から曖昧にしないことの両方が要る。

## 判断

- 新しい Router / Retriever / Selector は `research/<method-name>` ブランチで実装し、
  unit test を付ける。
- 評価は `Object-Routing-Research` から、Marmo-Core の commit SHA を固定して行う。
  結果 JSON には `_provenance.py` が SHA を刻む。
- 有効性が確認できた手法だけを `main` への PR にする。無効だった手法は `main` に入れず、
  比較結果と実験条件を Research 側に残す。
- Marmo-Core 本体を Research 側にコピーしない。

## 影響

- 研究用の実装も `ARCHITECTURE.md` の拡張ポイントに差し込む形を優先し、Kernel の既定挙動を
  変えない。
- `benchmarks/results/*.json` は凍結物として扱い、実装差分なしに数値を変えない。

## 代替案

- Research 側に実装を持つ: 実装の正が二重化し、論文と公開版の対応が崩れるため却下。
- `main` で直接実験する: PyPI 版に未検証の手法が混入するため却下。
