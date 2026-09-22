# 0004. サードパーティ Skill コーパスは git と配布物から除外する

- 状態: Accepted
- 日付: 2026-09-17
- 根拠: 6ef6ad03、583473e1（CHANGELOG 0.5.0）、`MANIFEST.in` のコメント、`benchmarks/README.md`

## 文脈

ルーティングベンチマークは約 1,000 件（約 260MB）の外部リポジトリ由来の SKILL.md を使う。
収集は許容的ライセンス（MIT / Apache-2.0 / BSD-3 / MIT-0）に限定しているが、再配布条件の
整理は済んでいない。sdist に含めると `pip install` ごとに数百 MB を配ることにもなる。

## 判断

- `resources/skills` は `.gitignore` と `MANIFEST.in` の両方で除外し、再配布しない。
  出典は `resources/skills/SOURCES.md`（コーパスと一緒に git 管理外）に記録する。
- コーパスが無い環境で `run_benchmark.py` を実行すると、入手方法を案内して停止する。
- コーパスに依存しないスイート（集合選択、スケール、適応）は生成スクリプトだけで完結させ、
  配布物からも動くようにする。

## 影響

- ベンチマークの完全再現には `tools/collect_skills.py` による再収集（GitHub トークンが要る）か、
  手元のコーパスの `--resources` 指定が要る。
- 結果 JSON は比較の基準としてコミットし、コーパスの版は `SOURCES.md` で追う。

## 代替案

- Git LFS で同梱する: ライセンス整理が済んでいないため却下。
- 合成コーパスだけにする: 実在の SKILL.md の語彙の偏りが測れないため、補完に留める。
