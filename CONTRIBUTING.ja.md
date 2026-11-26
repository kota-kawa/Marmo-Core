# Marmo-Core へのコントリビュート

English version: [CONTRIBUTING.md](CONTRIBUTING.md).

## セットアップ

Marmo-Core は Python 3.10〜3.14 に対応し、実行時の依存関係を最小限に保っています。必須の依存パッケージは `python-dotenv` のみです。実行時依存を追加する前に、まず issue で相談してください。実行時に必要でないものは `dev` または `benchmark` extra に追加します。

```bash
python -m pip install -e '.[dev]'
```

## テスト

```bash
python -W error::ResourceWarning -m unittest discover -s tests
```

`-W error::ResourceWarning` は省略できません。CI もこの方法で実行するため、テストのアサーションが通っていても、閉じ忘れたファイルやソケットがあるとビルドは失敗します。

## ブランチとプルリクエスト

`main` はリリース済みの安定ブランチで、直接 push してはいけません。`<type>/<topic>` 形式の名前を付けたブランチ（`fix/`、`feat/`、`docs/`、`chore/`、`ci/`）で作業し、プルリクエストを作成してください。評価中の新しいルーティング手法は `research/<method-name>` で作業します（[AGENTS.md](AGENTS.md) を参照）。

- コミット件名は既存の履歴に合わせて `<type>: <English summary>` とします。修正によって挙動が変わる場合は、本文に何が問題だったか、何を測定したか、トレードオフは何かを書いてください。
- バグ修正とリファクタリング、機能追加と整形など、種類の異なる変更は別コミットにしてください。
- プルリクエストのタイトルと説明には日本語と英語の両方を含め、[.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) に従ってください。変更内容、関連 issue、実行したテストコマンドと結果、レビュー担当者が判断する必要のある事項（既定値、終了コード、スコア、公開名の変更など）を書きます。
- 利用者に見える変更は、同じプルリクエストで `## [Unreleased]` の下に追記してください。バージョン更新は、別のメンテナ作業として行います（「リリース」を参照）。

マージ条件と必須の CI ジョブは [.github/BRANCH_PROTECTION.md](.github/BRANCH_PROTECTION.md) に記録されています。

## CI のローカル再現

CI では、対応するすべての Python バージョンでテストスイートを実行し、以下の静的解析とリリース検査も実行します。プルリクエストを作成する前に実行してください。

```bash
ruff check marmo_core tests scripts tools
mypy marmo_core
python scripts/release_check.py
python scripts/check_doc_paths.py
python scripts/check_env_documentation.py
check-manifest
python -m build
python -m twine check dist/*
check-wheel-contents dist/*.whl
```

ファイルを追加した後に `check-manifest` が不一致を報告した場合、そのファイルを sdist に含めるには `MANIFEST.in` に対応する規則を追加してください。リポジトリ内だけで使う場合は、`pyproject.toml` の `[tool.check-manifest] ignore` に列挙してください。

`check_doc_paths.py` は、Markdown 文書に記載されたリポジトリ内のパスが存在しない場合に失敗します。参照を修正するか、意図的に追跡対象外としているパスを記載する場合は、その理由とともにスクリプトの許可リストへ追加してください。`check_env_documentation.py` は `.env.example` と `marmo_core/` または `benchmarks/` が読み取る環境変数の不一致を検出します。新しい環境変数と `.env.example` の行は、同じ変更で追加してください。

Docker ジョブもイメージをビルドし、コンテナ内でテストスイートを実行します。

```bash
docker build --tag marmo-core:ci .
docker run --rm marmo-core:ci python -m unittest discover -s tests
```

## リソースサンプル

`resources/memory`、`resources/tools`、`resources/agents` に含まれるサンプルは実行可能で、テスト対象です。新しいサンプルでは、`python:` 参照から動作する実装を解決できるようにし、実際に必要な権限と副作用を宣言し、ファイルシステムアクセスを現在の作業ディレクトリ内に限定してください。次のコマンドで変更を検証します。

```bash
marmo validate resources/memory resources/tools resources/agents
```

## ドキュメント

- [ARCHITECTURE.md](ARCHITECTURE.md) は、レイヤー、`Kernel.run_goal` を通るリクエスト経路、契約、拡張ポイントをまとめた内部設計の参照文書です。
- [docs/knowledge/](docs/knowledge/README.md) には、開発規約、デバッグ手順、互換性契約、このリポジトリの履歴から記録した教訓があります。コードを変更する前に `docs/knowledge/development_conventions.md` を読んでください。
- [docs/decisions/](docs/decisions/README.md) にはアーキテクチャ上の判断を記録します。判断を変更するときは ADR を追加または更新してください。
- [AGENTS.md](AGENTS.md) は各文書の参照時期を記載し、コーディングエージェントの規則を定めています。文書を追加または削除したときは、同じコミットでこの一覧も更新してください。CI が記載されたパスの存在を検査します。

## セキュリティに関わる変更

権限、副作用の分類、ポリシー評価、シークレット処理、human-in-the-loop のゲートに関する変更は、[docs/threat-model.ja.md](docs/threat-model.ja.md) と照らしてレビューしてください。信頼境界を移す場合は、その文書も更新してください。脆弱性の報告先は、プルリクエストではなく [SECURITY.ja.md](SECURITY.ja.md) を確認してください。

## リリース

リリースは `.github/workflows/release.yml` が Trusted Publishing を通じて PyPI に公開します。このワークフローは、タグとパッケージのバージョンが一致しない場合、公開を拒否します。

1. `marmo_core/_version.py` と `pyproject.toml` の**両方**のバージョンを更新します。値が異なると `scripts/release_check.py` が失敗します。
2. `CHANGELOG.md` に `## [x.y.z] - YYYY-MM-DD` の節を追加し、ファイル末尾の比較リンクも更新します。日付付きの節がない新バージョンは `release_check.py` が失敗します。
3. 上記の検査を実行してから、コミットし `main` にマージします。
4. 必要に応じて `Release` ワークフローを手動で実行（`workflow_dispatch`）し、先に TestPyPI へ公開して、プロジェクトページの表示を確認します。
5. 最新の `main` をチェックアウトし、リリースするコミットにタグを付けて push します。

   ```bash
   marmo_release_tag="v$(python -c 'from marmo_core import __version__; print(__version__)')"
   git tag "$marmo_release_tag" && git push origin "$marmo_release_tag"
   ```

アップロードの実行前に `pypi` 環境での承認が必要です。
