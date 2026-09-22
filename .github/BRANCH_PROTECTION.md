# Branch protection for `main`

`main` のマージ条件と CI ゲートの記録。GitHub 上の設定を変えたら、この文書を同じ PR で
更新する。

## 現状（2026-09-23 確認）

- GitHub のブランチ保護ルールと Rulesets は **未設定**（`gh api repos/kota-kawa/Marmo-Core/branches/main/protection` が 404、`rulesets` が空）。
- `main` へ直接 push しないことと、PR 経由で取り込むことは、`AGENTS.md` の規則として運用している。
- 直接 push を技術的に禁止したい場合は、下記「推奨設定」をメンテナが GitHub の Settings →
  Branches（または Rulesets）で有効にし、この節を更新する。

## 必須 CI チェック（`.github/workflows/ci.yml`）

PR が `main` に入る前に、次のジョブが緑であること。

| ジョブ名 | 内容 |
|---|---|
| `Python 3.10` 〜 `Python 3.14` | `python -W error::ResourceWarning -m unittest discover -s tests` |
| `Static and release checks` | `ruff check`、`mypy marmo_core`、`release_check.py`、`check_doc_paths.py`、`check_env_documentation.py`、`check-manifest`、`build`、`twine check`、`check-wheel-contents` |
| `Docker` | イメージをビルドし、コンテナ内でテストを実行 |

## 推奨設定

- Require a pull request before merging（レビュー数はメンテナの判断。現状は単独メンテナ）。
- Require status checks to pass before merging: 上表の 7 ジョブ。Require branches to be up to date は任意。
- Do not allow bypassing the above settings（管理者にも適用）。
- Restrict force pushes / deletions。

## 運用上の注意

- CI の `concurrency` は同じ ref の実行中ジョブを打ち切る（`cancel-in-progress: true`）。
  `main` に連続してマージすると中間コミットの実行が打ち切られるので、リリースタグを打つ前に
  `main` の最新コミットの CI が完了して緑であることを確認する。
- `release.yml` は `v*` タグの push で走り、タグと同梱バージョンが一致しないと止まる。
  `pypi` environment は承認が要る。
