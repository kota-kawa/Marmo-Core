# Architecture Decision Records

重要な技術判断の記録。判断を変更・追加するときは、既存 ADR を確認し、理由と影響を
更新または新しい ADR として記録する。ファイル名は `NNNN-<slug>.md`、状態は
Accepted / Superseded / Deprecated。

| ADR | 判断 | 状態 |
|---|---|---|
| `0001-single-runtime-dependency.md` | 実行時依存は `python-dotenv` のみ。モデル系は extra とプロバイダ ABC で隔離 | Superseded（0007） |
| `0002-research-branches-and-frozen-sha.md` | 研究手法は `research/*` ブランチで実装し、評価は commit SHA を固定して別リポジトリから行う | Accepted |
| `0003-absolute-relevance-and-bm25f.md` | 関連度成分を絶対値にし、SKILL.md 本文を割り引いた BM25F で索引する | Accepted |
| `0004-third-party-skill-corpus-not-redistributed.md` | ベンチマーク用のサードパーティ Skill コーパスは git と配布物から除外する | Accepted |
| `0005-constraints-solved-by-selector-not-llm.md` | 集合選択の制約は宣言メタデータをソルバーで解き、LLM や検索時フィルタに委ねない | Accepted |
| `0006-provider-failures-terminate-the-task.md` | プロバイダ失敗はタスクを `failed` で終端させ、監査ログを残す。CLI 終了コードは 1 | Accepted |
| `0007-minimal-runtime-dependencies-with-user-approval.md` | 実行時依存は最小限に保ち、追加はユーザーに必要性と影響を示して確認を取る | Accepted |
| `0008-timeout-outcome-is-uncertain.md` | timeout 後の副作用を結果不明として扱い、自動再実行しない。停止可能な実行方式を追加する | Accepted |
| `0009-task-budget-reservations.md` | タスク予算を固定し、モデルと Resource の実行前に予約する | Accepted |
| `0010-execution-snapshot.md` | 再開時は保存した選択 Resource と compiled context を検証して復元する | Accepted |

## 書き方

```markdown
# NNNN. タイトル

- 状態: Accepted
- 日付: YYYY-MM-DD
- 根拠: commit / PR / CHANGELOG の参照

## 文脈
## 判断
## 影響
## 代替案
```

ADR を追加したらこの表を更新する。判断の背景となる実測は `benchmarks/README.md` に、
利用者向けの説明は `CHANGELOG.md` に書き、ADR には判断と理由だけを書く。
