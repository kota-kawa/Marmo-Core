# デバッグ手順

コードを読み始める前に、症状から該当する節を引く。過去に実際に起きた不具合が根拠
（`lessons_from_history.md`）。

## 実モデルでツールが呼ばれない・HTTP 400 が返る

1. `--llm mock` で同じゴールを実行し、検索・選択・ゲートまでは動くか確認する。
2. `ProviderHTTPError` のメッセージにステータスと API のメッセージ本文が入っている。
   よくある原因: ツール名にドット（`ToolNameCodec` を迂回していないか）、
   `max_tokens` と `max_completion_tokens` の取り違え、`OPENAI_REASONING_EFFORT=none`
   を Groq に送っている、`ANTHROPIC_MAX_TOKENS` 未設定。
3. 403 で Cloudflare の error 1010 なら User-Agent。プロバイダは `marmo-core/<version>` を
   付けているはずなので、独自 transport を使っていないか確認する。
4. 401 で API キーが空なら、`.env` の場所（最寄りのものを `override=False` で読む）と
   `OPENAI_BASE_URL` の組み合わせを確認する。**`.env` の中身は読まない**。
   `.env.example` と照らして変数名だけを確認する。

## 検索がおかしい（正解が候補に出ない・無関係なものが選ばれる）

1. `marmo search <paths> --task "..." --format json` で候補と `relevance` を見る。
   関連度は絶対値（クエリ語をすべて 1 回含む文書を 1.0）なので、0.2 以下は「ほぼ一致なし」。
2. 種別ごとの枯渇: 大きな Skill カタログと少数の Tool を混ぜたとき、Tool が候補に
   出ないなら per-kind top-up が動いていない。`--per-kind-limit` と `set_limits` を確認。
3. 本文で勝っている Skill: `BODY_FIELD_WEIGHT`（0.25）で割り引かれているはず。
   メタデータの `description` / `capabilities` が空でないか確認する。
4. 日本語のゴール: CJK バイグラムの雑音で無関係なものが 0.3 前後まで上がる（既知）。
   `--retriever hyde` で英語メタデータに寄せる。
5. `SKILL.md` が読み込まれない: フロントマターの `description: >-` などブロックスカラー、
   BOM、非 UTF-8。`marmo validate` の警告に壊れたファイル名が出る。
6. スコアが変わらない・キャッシュが効かない: `ResourceRegistry.content_revision` が
   動いたかどうか。`stats` だけの更新では索引と埋め込みは再構築されない（意図した挙動）。

## タスクが `completed` なのに何もしていない

- `TaskResult.detail` を読む。「一致なし」「Tool がモデルに届かなかった」はここに出る。
- `--strict` を付けると両方が exit 1 になる。自動化では常に `--strict`。
- 一時停止からの再開で権限不足によりスキップされた場合、resume コマンドの
  `--granted-permission` / `--allow-side-effect` が落ちていないか確認する。

## 監査ログが空・タスクが `running` のまま

- 例外がカーネルの外に出ている。`ProviderError` 以外の例外がループから漏れていないか、
  `--audit-log` が失敗時にも書かれるかを確認する（0.5.0 で修正済みの経路）。
- `AuditLog.from_jsonl` が `ValueError` を出すならハッシュチェーンが壊れている。
  レコードを手で編集していないか。

## CI が落ちる（テストは通るのに）

| ジョブの失敗 | 原因と対処 |
|---|---|
| `ResourceWarning` | ファイル・ソケット・SQLite 接続の閉じ忘れ。`with` か `addCleanup` |
| `check-manifest` | 追跡ファイルの追加。`MANIFEST.in` に足すか `pyproject.toml` の ignore に足す |
| `release_check.py` | `_version.py` と `pyproject.toml` の不一致、または CHANGELOG に現行版の節が無い |
| `check_doc_paths.py` | 文書が存在しないパスを指している。参照を直すか、意図的に未追跡なら allowlist に理由付きで追加 |
| `check_env_documentation.py` | 環境変数の読み取りと `.env.example` の不一致。同じ変更で両方を揃える |
| `mypy` | ローカルで numpy などが入っていると、その `.pyi` が `python_version = "3.10"` 設定で構文エラーになり `errors prevented further checking` で止まる（CI 環境には入っていないので通る）。`marmo_core` 以外のエラーなら、依存を外した環境か `python -m venv` で再実行して判断する |
| Docker | イメージに必要なファイルが無い。`.dockerignore` は `*.md` を除外し `CHANGELOG.md` だけ残す |

## ベンチマークが再現しない

- コーパス `resources/skills` は git 管理外。無ければ `run_benchmark.py` が案内付きで止まる。
- `hybrid-model` の初回は全件埋め込みで約 140 秒。2 回目以降は `content_revision` 単位で
  キャッシュされる。
- HyDE / 再ランク / LLM Set Selector は `benchmarks/cache/` の JSON キャッシュに当たれば
  LLM を呼ばず決定的に再現する。キャッシュが無い環境では `OPENAI_API_KEY` が要る。
- レイテンシは測定機の負荷で 2 倍程度動く。精度指標だけを比較する。
- 結果 JSON の `provenance` に commit SHA が入る。数値を比較する前に SHA を揃える。
