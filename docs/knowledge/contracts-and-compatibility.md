# 契約と互換性

Marmo-Core は SemVer に従い、同一メジャー内で次の表面を壊さない。守り方は
`tests/test_compatibility.py` と `tests/fixtures/compat/`。

## 契約の一覧

| 表面 | 定義 | 守るテスト | 変え方 |
|---|---|---|---|
| 公開 API | `marmo_core/__init__.py` の `__all__` | `test_v030_public_api_remains_available`（`fixtures/compat/v0.3.0/public_api.txt` の全名前が残ること） | 追加は自由。削除・改名は次のメジャーまで非推奨期間を置き、CHANGELOG に書く |
| リソース定義 | `ResourceDefinition` / `ResourceMetadata`（`models.py`）。フラット形式と `{"metadata": ...}` 形式 | `test_v030_resource_defaults_new_optional_metadata` | 新フィールドは任意かつ既定値付きで追加する。必須フィールドを増やさない |
| 状態ファイル | `<task_id>.jsonl`、`schema_version: 1`、`EVENT_KINDS` | `test_v030_jsonl_state_loads_and_accepts_new_events` | 新しい event kind は追加してよい。既存 kind の payload の意味を変えない。形式を変えるなら `schema_version` を上げて旧版を読めるようにする |
| 監査ログ | `AuditRecord` のフィールドとハッシュ計算 | `test_policy_audit.py`、`test_safety.py` | ハッシュ対象や正規化を変えると過去ログの `verify()` が失敗する。変える場合は版を付けて両方検証する |
| CLI | サブコマンド、フラグ、終了コード（0 / 1 / 2）、`--strict` の失敗条件 | `test_cli_release.py`、`test_v1.py` | フラグの削除・意味変更、終了コードの変更は CHANGELOG の Changed に明記する（0.5.0 でプロバイダ失敗の終了コードを 2→1 に変えた前例） |
| プロバイダ wire 形式 | `ToolNameCodec`、`max_tokens` の選択、予算付き `complete_bounded()`、エラーの `ProviderHTTPError` 化、伏せ字 | `test_provider_compat.py` | 固定応答テストを先に書く。実 API の仕様変更は CHANGELOG の Fixed |
| タスク予算 | `TaskBudget`、追記型の `budget` event、各モデル / Resource の予約と精算 | `test_task_budget.py`、`test_provider_compat.py` | 予算付きカスタム LLM は `complete_bounded()` と `supports_output_token_limit=True` を実装する。入力上限は serialized messages と Tool schema の推定値で判定する |
| 検索スコアの尺度 | 関連度成分は絶対値（0.6.0 以降） | `test_retrieval_scoring.py`、ベンチマーク | 尺度を変えたら `Kernel(min_relevance)`、ベンチマーク既定値、README の数値を同時に更新し、CHANGELOG に「しきい値の再校正が要る」と書く |
| 環境変数 | `.env.example` | `scripts/check_env_documentation.py` | 追加・削除は同じ変更で `.env.example` と README の該当節を更新 |
| 配布物 | `MANIFEST.in`、`pyproject.toml`、Docker イメージの内容 | `check-manifest`、`check-wheel-contents`、Docker ジョブ | sdist 内でテストが完結すること（フィクスチャ、examples、scripts を同梱） |

## 凍結物の扱い

- `tests/fixtures/compat/v0.3.0/` は書き換えない。新しい契約を凍結するときは
  `tests/fixtures/compat/v<version>/` を追加し、`test_compatibility.py` に対応するテストを
  足す。
- `benchmarks/results/*.json` は測定結果の凍結物。実装差分なしに数値だけを変えない。

## 互換性を壊す変更の手順

1. ADR を書く（`docs/decisions/`）。理由、影響を受ける利用者、移行手順。
2. 可能なら非推奨期間を置く（旧名を残して `DeprecationWarning`）。
3. `CHANGELOG.md` の Changed または Removed に、利用者が何をすればよいかを書く。
4. `README.md` と `docs/` の該当箇所を同じ PR で直す。
5. バージョンはメンテナが決める。PR にはバージョン変更を含めず、必要なら別コミットで提案する。

## 過去の契約変更

- 0.5.0: プロバイダ失敗時の CLI 終了コードを 2→1（例外で落ちる代わりに `failed` で終端）。
  `--max-tool-output-tokens` 既定 8000 で大きなツール出力が切り詰められる。
- 0.6.0: 関連度成分を相対正規化から絶対値へ。既存のしきい値は再校正が要る
  （ベンチマーク既定 0.55→0.35）。`RuleBasedSetSelector` が `min_relevance` を尊重する
  ようになった。
- Unreleased: timeout 後の自動 retry/fallback を停止。明示的に timeout を
  `RetryPolicy.retry_kinds` に指定しても、不明な副作用を重複させないため人の判断を求める。
  `timeout_mode="process"` は追加の選択肢で、既定は互換性のため `thread` のまま。
- Unreleased: `budget` event に設定・予約・精算を追加。予算を付けた task は同じ設定で
  再開する必要がある。予算なしの従来 task の形式と挙動は変えない。
  provider 応答に token usage が無い場合や provider 呼び出しが例外になった場合は予約額全額を
  課金扱いする。
  provider 応答に token usage が無い場合は空の usage として表し、予算付き task は
  予約額全額を課金扱いする。provider 呼び出しが例外になった場合も使用量不明として予約額全額を
  課金扱いする。
- Unreleased: `snapshot` event に選択結果を保存し、再開時の再検索・再選択を避ける。
  選択 Resource、activation 済み memory / skill 本文、またはコンパイル済み実行 context の
  fingerprint が異なれば task を失敗させる。snapshot 導入前の activation / execution pause は
  安全に復元できないため失敗させる。
