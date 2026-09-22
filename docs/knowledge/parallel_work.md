# 並行作業（git worktree）の運用

判断基準は `AGENTS.md` の「サブエージェントと git worktree」。ここには分けた後の手順を書く。

## 作る

```bash
git -C /path/to/Marmo-Core fetch origin
git -C /path/to/Marmo-Core worktree add ../Marmo-Core-<topic> -b <type>/<topic> origin/main
cd ../Marmo-Core-<topic>
python -m pip install -e '.[dev]'        # editable install は worktree ごとに必要
```

- `.env` は git 管理外なので新しい worktree には無い。モック LLM のテストとベンチマークの
  非 LLM 構成は `.env` 無しで動く。実モデルの確認が要る作業だけ、`.env.example` を見て
  必要な変数を **環境変数として** 渡す（`.env` をコピーして中身を読まない）。
- `resources/skills`（ベンチマークコーパス）も git 管理外。必要なら
  `run_benchmark.py --resources <path>` で元の checkout のディレクトリを指す。

## 分ける単位

- 1 worktree = 1 ブランチ = 1 PR。着手前に決め、途中で思いつきで分割しない。
- 同時に走る作業が同じファイルを編集する予定なら、worktree を増やしても解決しない。
  片方を待たせる。衝突しやすいファイル: `CHANGELOG.md` の `## [Unreleased]`、
  `marmo_core/__init__.py` の `__all__`、`marmo_core/kernel.py`、`benchmarks/README.md`、
  `benchmarks/results/*.json`、`AGENTS.md` の文書一覧。
- 並列作業中は担当 worktree の外を触らない。他の作業への依存が判明したら止めてユーザーに
  報告する。

## 共有される状態

- **ベンチマーク結果**: 2 つの worktree が同じ `benchmarks/results/<name>.json` を書くと
  後勝ちになる。結果を更新する作業は同時に 1 つ。`--output` で別名に書き、比較してから
  正本を更新する。
- **`benchmarks/cache/`**: LLM 応答キャッシュ。場所はスクリプト内の定数で、worktree ごとに
  別ディレクトリになる。キャッシュ命中による決定的な再現が要るなら、元の checkout から
  ディレクトリをコピーする。
- **状態ディレクトリ**: `marmo run --state-dir` の既定はカレントディレクトリ配下。
  worktree ごとに分かれるので衝突しない。
- **ポート・DB**: 本ライブラリは常駐サーバーを持たない。`SQLiteStateStore` はファイル単位。

## 終わったら

```bash
git -C /path/to/Marmo-Core worktree remove ../Marmo-Core-<topic>
git -C /path/to/Marmo-Core branch -d <type>/<topic>        # マージ後
```

`main` への連続マージは、直前のマージの CI 完了を待ってから行う（`AGENTS.md`）。
