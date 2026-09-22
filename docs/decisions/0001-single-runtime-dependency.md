# 0001. 実行時依存は `python-dotenv` のみ

- 状態: Accepted
- 日付: 2026-08-07
- 根拠: 49076f8b（Document minimal dependency policy）、`CONTRIBUTING.md` Setup、`pyproject.toml`

## 文脈

Marmo-Core はエージェントランタイムに組み込まれるカーネルであり、利用者の依存解決を
汚さないことが採用の前提になる。一方で埋め込みモデルや cross-encoder はベンチマークに要る。

## 判断

- 実行時依存は `python-dotenv` の 1 つだけ。HTTP は `urllib`、永続化は JSONL / `sqlite3`、
  フロントマターは自前パーサ。
- モデル系は `benchmark` extra（fastembed）に置き、コアは `EmbeddingProvider` /
  `CrossEncoderProvider` / `LLMProvider` の ABC だけを持つ。
- 開発ツールは `dev` extra。Dependabot は GitHub Actions だけを対象にする（PR #8）。

## 影響

- 新しい実行時依存は issue で合意してから。PR に理由と影響を書く。
- 数値計算は純 Python で書く。1,000 件規模ではコサイン類似度も許容範囲だが、10k 件以上では
  階層型ルーティング（`hierarchy.py`）が前提になる（`benchmarks/README.md`）。

## 代替案

- `httpx` / `pydantic` / `numpy` を採用する: 利便性は上がるが、組み込み先との依存衝突と
  インストールサイズが採用障壁になるため却下。
