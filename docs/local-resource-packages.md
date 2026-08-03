# ローカルリソースパッケージ

Marmo-Core のローカルリソースパッケージは、Memory・Skill・Tool・Agent を同じ形式で共有し、読み込み前に互換性と改変の有無を検査するための仕組みです。追加依存はありません。

完成した例は [`examples/package-template`](../examples/package-template) にあります。

## ディレクトリ構成

```text
my-package/
  marmo-package.json       # パッケージmanifest（手で編集）
  marmo-package.lock.json  # SHA-256固定と取得元（CLIで生成）
  resources.json           # 1個以上のリソース定義
  skills/
    review/SKILL.md        # manifestから列挙すれば利用可能
```

manifestに列挙されていないファイルはパッケージとして読み込みません。絶対パス、`..`、パッケージ外を指すシンボリックリンクは拒否します。

## manifest

ファイル名は必ず`marmo-package.json`です。

```json
{
  "schema_version": 1,
  "namespace": "com.example",
  "name": "operations",
  "version": "1.2.0",
  "description": "Operations resources",
  "kernel": ">=0.3.0,<1.0.0",
  "resources": ["resources.json", "skills/review/SKILL.md"],
  "dependencies": [
    {"name": "com.example/foundation", "version": "^1.0.0"}
  ]
}
```

各フィールドの意味は次のとおりです。

| フィールド | 必須 | 内容 |
|---|---:|---|
| `schema_version` | Yes | 現在は`1` |
| `namespace` | Yes | 小文字英数字・`-`・`.`からなる所有名前空間 |
| `name` | Yes | 名前空間内のパッケージ名 |
| `version` | Yes | パッケージのSemVer |
| `description` | No | パッケージの説明 |
| `kernel` | Yes | 対応するMarmo-Coreのバージョン範囲 |
| `resources` | Yes | パッケージルートからの相対ファイルパス |
| `dependencies` | Yes | 同時に読み込むローカルパッケージと、そのバージョン範囲 |

バージョン範囲は、完全一致、`>`、`>=`、`<`、`<=`、カンマ区切りのAND、caret（`^1.2.3`）、tilde（`~1.2.3`）、`*`に対応します。`||`によるORは未対応です。

パッケージ名は`namespace/name@version`（例: `com.example/operations@1.2.0`）として識別されます。同じ親ディレクトリを読み込むと、配下のパッケージを検出し、依存先の存在とSemVer範囲を検査します。

## リソース定義

JSONは従来どおり、単一リソース、リソースの配列、または`{"resources": [...]}`を使用できます。共通メタデータ、実体、依存宣言、種別固有メタデータを一つのエントリで表現します。

```json
{
  "id": "tool.com.example.read-report",
  "kind": "tool",
  "name": "Read report",
  "version": "1.0.0",
  "description": "Read one report.",
  "capabilities": ["report reading"],
  "input_summary": "A report path",
  "output_summary": "Report text",
  "required_permissions": ["fs.read"],
  "cost_estimate": 0.0,
  "latency_class": "fast",
  "side_effect": "read",
  "trust_level": "verified",
  "ref": "tool://com.example/read-report",
  "tags": ["report"],
  "dependencies": ["memory.com.example.report-policy@1.0.0"],
  "input_schema": {
    "type": "object",
    "required": ["path"],
    "properties": {"path": {"type": "string"}}
  },
  "output_schema": {"type": "object"},
  "isolation_level": "L2"
}
```

リソースIDは、種別とmanifestの名前空間を含む`<kind>.<namespace>.<local-name>`形式でなければなりません。たとえばnamespaceが`com.example`なら、Toolは`tool.com.example.*`、Agentは`agent.com.example.*`です。この検査により、別パッケージの名前空間を誤って上書きできません。

種別固有の主な実体フィールドは以下です。

- Memory: `content`
- Skill: `instructions`（または`SKILL.md`本文）
- Tool: `input_schema`、`output_schema`、`isolation_level`
- Agent: `delegation_interface`、`model`、`system_prompt`

`SKILL.md`をmanifestから読み込む場合は、名前空間検査に通るようフロントマターで`id`を指定します。

```markdown
---
id: skill.com.example.review
name: review
version: 1.0.0
description: Review a report.
dependencies: [memory.com.example.report-policy@1.0.0]
---
```

## ロックと検証

manifestとリソースをレビューした後、ロックを作成します。

```bash
marmo package lock ./my-package
marmo package verify ./my-package
marmo package inspect ./my-package
marmo validate ./my-package
```

`marmo-package.lock.json`には次を記録します。

- パッケージの完全なidentity
- 取得元種別`local`と、移動可能な取得元パス（既定`.`）
- manifestのSHA-256
- manifestに列挙した各リソースのSHA-256

manifestやリソースを意図的に変更した場合は、差分をレビューしてから`marmo package lock`を再実行します。ロック不在、ファイル追加・削除、ハッシュ不一致、カーネル非互換、依存パッケージ不足は、Registryへ1件も登録する前に拒否されます。

ロックは「レビュー済みのローカル内容から変わっていないこと」を確認する仕組みであり、作者の身元を証明する暗号学的署名ではありません。署名と公開レジストリはv3の範囲です。信頼できない取得物に対して、自分で内容を確認せずロックを作り直さないでください。

取得元を親ディレクトリ基準で記録する場合は次のように指定できます。絶対パスと`..`は拒否されます。

```bash
marmo package lock ./packages/operations --source packages/operations
```

## Python API

```python
from marmo_core import load_registry, verify_local_package

package = verify_local_package("./my-package")
print(package.manifest.identity)

registry = load_registry(["./my-package"])
```

別バージョンのカーネルに対する互換性を事前検査する場合は、`load_registry(..., kernel_version="0.4.0")`または`verify_local_package(..., kernel_version="0.4.0")`を使えます。

## 公開前チェックリスト

1. namespaceを自分の管理範囲にし、全リソースIDをその配下にする。
2. パッケージと各リソースのSemVerを意図どおり更新する。
3. 必要最小限の権限・副作用・trust level・隔離レベルを宣言する。
4. 依存するパッケージとリソースを列挙する。
5. `marmo package lock`後にmanifest、取得元、全ハッシュをレビューする。
6. `marmo package verify`と`marmo validate`を実行する。
7. 実行可能なTool / Agentは、Policy Gatewayを通る統合テストを用意する。
