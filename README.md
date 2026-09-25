> 一番下に日本語版もあります

# Marmo-Core

![Marmo Core: a sleeping marimo beside the title and tagline](https://raw.githubusercontent.com/kota-kawa/Marmo-Core/main/assets/readme-banner.png)

[![PyPI](https://img.shields.io/pypi/v/marmo-core.svg)](https://pypi.org/project/marmo-core/)
[![Python versions](https://img.shields.io/pypi/pyversions/marmo-core.svg)](https://pypi.org/project/marmo-core/)
[![CI](https://github.com/kota-kawa/Marmo-Core/actions/workflows/ci.yml/badge.svg)](https://github.com/kota-kawa/Marmo-Core/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Marmo-Core is a Python library and CLI for finding resources that fit an AI agent's goal and running them through permission and policy checks. It combines resource registration, search, selection, execution, human approval, and audit records in one kernel. Start offline with a deterministic mock model, then connect an OpenAI-compatible or Anthropic model.

## What it manages

| Resource | Purpose |
| --- | --- |
| Memory | Information added to the agent's context. |
| Skill | Instructions the agent can use for a task. |
| Tool | A callable operation with a declared input schema and permissions. |
| Agent | A task delegated to another execution boundary. |

For each goal, the kernel searches a registry, selects resources, checks policy before activation and execution, calls the model, and records the outcome. Tools and Agents can be denied or paused for human approval. The [threat model](docs/threat-model.md) describes the security boundaries and their limits.

## Install

Requires **Python 3.10 or newer**.

```bash
python -m pip install marmo-core
```

The `marmo` CLI and Python API are installed together. No API key is needed for the offline examples below.

## Try it offline

### Python: run one Tool

This complete example registers an addition Tool, grants its declared permission, and runs a goal with the mock model. The model's arguments are fixed so the result is reproducible.

```python
from marmo_core import (
    Kernel, MockLLMProvider, PolicyContext, ResourceDefinition, ResourceRegistry,
)


def add_numbers(a: float, b: float) -> dict:
    return {"sum": a + b}


registry = ResourceRegistry()
registry.add(ResourceDefinition.from_mapping({
    "id": "tool.math.add", "kind": "tool", "name": "Add Numbers", "version": "1.0.0",
    "description": "Add two numbers and return their sum.",
    "capabilities": ["arithmetic"], "input_summary": "Two numbers a and b.",
    "output_summary": "Object with the sum.", "required_permissions": ["math.add"],
    "cost_estimate": 0.0, "latency_class": "fast", "side_effect": "none",
    "trust_level": "core", "ref": "tool://math/add", "tags": ["math"],
    "input_schema": {"type": "object", "required": ["a", "b"],
                     "properties": {"a": {"type": "number"}, "b": {"type": "number"}}},
}))

kernel = Kernel(
    registry,
    MockLLMProvider(tool_arguments={"tool.math.add": {"a": 2, "b": 3}}),
    policy_context=PolicyContext(granted_permissions=("math.add",)),
    tool_implementations={"tool.math.add": add_numbers},
)
result = kernel.run_goal("Add 2 and 3 with the calculator tool")
print(result.status, result.output)
```

The status is `completed`, and the Tool result contains `{"sum": 5}`. For a runnable file that also prints and verifies the audit trail, see [`examples/hello_world.py`](examples/hello_world.py).

### CLI: inspect and run a bundled example

The resource files in these commands live in this repository. Clone it first if you installed only the PyPI package:

```bash
git clone https://github.com/kota-kawa/Marmo-Core.git
cd Marmo-Core
marmo validate examples/resources
marmo search examples/resources --task "read a local text file safely"
```

Run the bundled JSON validation Tool without a model account or manual Python binding:

```bash
marmo run resources/tools/validate-json.json \
  --task "validate JSON input" \
  --tool-args '{"tool.marmo.samples.validate-json":{"value":{"name":"Marmo"},"schema":{"type":"object","required":["name"],"properties":{"name":{"type":"string"}}}}}' \
  --strict --format json
```

`--tool-args` supplies calls to the mock model; it does not ask a model to choose arguments. The repository also includes ten samples each of Memory, Tool, and Agent resources under `resources/`. The Tool and Agent samples have executable handlers.

## Use a real model

Create a `.env` file in your working directory, or set the same variables in your shell. In a source checkout, start from the template:

```bash
cp .env.example .env
```

| Provider | Required environment variables |
| --- | --- |
| OpenAI-compatible | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| Anthropic | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_MAX_TOKENS` |

The model name and maximum token setting can instead be passed to the corresponding Python provider constructor. `OPENAI_BASE_URL` selects another OpenAI-compatible endpoint; leave it empty for `api.openai.com`. `OPENAI_REASONING_EFFORT` is optional and provider-specific. See [`.env.example`](.env.example) for the full configuration and examples. OS environment variables take precedence over `.env` values.

From the repository checkout, ask an OpenAI-compatible model to select file Tools:

```bash
marmo run resources/tools \
  --llm openai \
  --task "List the text files in the current directory, then read each one and tell me what they say" \
  --granted-permission fs.read \
  --allow-side-effect none --allow-side-effect read
```

Use `--llm anthropic` for Anthropic. With a real model, `--tool-args` is ignored: the model chooses the Tool and its arguments. The default lexical retriever matches resources against their English metadata. For a goal in another language, add `--retriever hyde`; it uses the selected real model to restate the goal in that vocabulary before retrieval.

The equivalent Python setup is:

```python
from marmo_core import HydeRetriever, Kernel, LexicalRetriever, OpenAICompatibleLLMProvider, load_registry

llm = OpenAICompatibleLLMProvider()
kernel = Kernel(load_registry(["resources/tools"]), llm, retriever=HydeRetriever(llm, LexicalRetriever()))
```

## Execution notes

- `--granted-permission` and `--allow-side-effect` control separate checks. The latter is a repeatable exact allowlist: permitting both no side effect and reads requires both values as shown above.
- `marmo run` uses the mock model by default. A skipped resource can be recoverable; use `--strict` in automation to fail when a resource is skipped, a Tool named in `--tool-args` is not evaluated, or retrieval finds no usable resource.
- On POSIX systems, `--timeout-mode process` stops importable Python Tool handlers with JSON-compatible inputs and outputs at the deadline. Local closures are rejected in this mode; Windows rejects process mode because child-process termination cannot be guaranteed. The default `thread` mode limits waiting but cannot stop a timed-out handler. A timeout requires human reconciliation before retry because an external effect may have completed.
- A Tool argument that misses its `input_schema` can be returned to a real model for correction. `--max-input-repairs` defaults to 2. Tool output sent to the model is capped at an estimated 8,000 tokens by default (`--max-tool-output-tokens`).
- CLI commands discover `resources`, `skills`, or `examples/resources` in the current directory when no path is given. For a connector-only run, use `--no-default-resources`.
- Bundled filesystem examples operate within the current working directory. External examples require their declared permissions and human approval. The notification example reads `MARMO_NOTIFICATION_<DESTINATION>_URL` from the environment, and the `format-code` example requires the `.[dev]` extra for Ruff.

Run `marmo --help` or `marmo run --help` for all CLI options.

## Learn more and contribute

| Guide | Contents |
| --- | --- |
| [Project website](https://project-kk.com/en/marmo) | Library overview, concepts, and usage guide. |
| [Built-in Connectors](docs/connectors.md) | Connector setup and usage. |
| [Local Resource Packages](docs/local-resource-packages.md) | Packaging and loading local resources. |
| [Benchmarks](benchmarks/README.md) | Routing evaluation and committed results. |
| [Architecture](ARCHITECTURE.md) | Kernel flow and extension points. |
| [Contributing](CONTRIBUTING.md) | Development setup, checks, and pull requests. |
| [Changelog](CHANGELOG.md) | Released and upcoming changes. |

For a bug report or feature request, use [GitHub Issues](https://github.com/kota-kawa/Marmo-Core/issues). Marmo-Core is distributed under the [Apache License 2.0](LICENSE).

<details>
<summary>日本語版 (クリックして展開)</summary>

## Marmo-Core とは

Marmo-Core は、AI エージェントの目標に合うリソースを探し、権限とポリシーを確認して実行するための Python ライブラリと CLI です。リソースの登録、検索、選択、実行、人による承認、監査記録を一つのカーネルにまとめます。まずは決定的なモックモデルでオフライン実行を試し、その後 OpenAI 互換または Anthropic のモデルに接続できます。

### 扱うリソース

| 種類 | 役割 |
| --- | --- |
| Memory | エージェントの文脈に加える情報。 |
| Skill | タスクで利用する手順や指示。 |
| Tool | 入力スキーマと必要な権限を宣言した呼び出し可能な処理。 |
| Agent | 別の実行境界で委任するタスク。 |

カーネルは目標ごとに登録済みリソースを検索・選択し、有効化と実行の前にポリシーを確認します。Tool と Agent は拒否されたり、人の承認待ちになったりします。保護の対象と限界は[脅威モデル](docs/threat-model.md)を参照してください。

### インストール

**Python 3.10 以降**が必要です。

```bash
python -m pip install marmo-core
```

Python API と `marmo` CLI が一緒にインストールされます。以下のオフライン例に API キーは不要です。

### オフラインで試す

#### Python: Tool を一つ実行する

次の例は加算 Tool を登録し、宣言された権限を付与して、モックモデルで目標を実行します。モデルに渡す引数を固定しているため、結果を再現できます。

```python
from marmo_core import (
    Kernel, MockLLMProvider, PolicyContext, ResourceDefinition, ResourceRegistry,
)


def add_numbers(a: float, b: float) -> dict:
    return {"sum": a + b}


registry = ResourceRegistry()
registry.add(ResourceDefinition.from_mapping({
    "id": "tool.math.add", "kind": "tool", "name": "Add Numbers", "version": "1.0.0",
    "description": "Add two numbers and return their sum.",
    "capabilities": ["arithmetic"], "input_summary": "Two numbers a and b.",
    "output_summary": "Object with the sum.", "required_permissions": ["math.add"],
    "cost_estimate": 0.0, "latency_class": "fast", "side_effect": "none",
    "trust_level": "core", "ref": "tool://math/add", "tags": ["math"],
    "input_schema": {"type": "object", "required": ["a", "b"],
                     "properties": {"a": {"type": "number"}, "b": {"type": "number"}}},
}))

kernel = Kernel(
    registry,
    MockLLMProvider(tool_arguments={"tool.math.add": {"a": 2, "b": 3}}),
    policy_context=PolicyContext(granted_permissions=("math.add",)),
    tool_implementations={"tool.math.add": add_numbers},
)
result = kernel.run_goal("Add 2 and 3 with the calculator tool")
print(result.status, result.output)
```

状態は `completed` となり、Tool の結果に `{"sum": 5}` が含まれます。監査記録の表示と検証も行う実行ファイルは [`examples/hello_world.py`](examples/hello_world.py) にあります。

#### CLI: 同梱サンプルを調べて実行する

次のコマンドで使うリソース定義ファイルはこのリポジトリ内にあります。PyPI パッケージだけをインストールした場合は、先にリポジトリを取得してください。

```bash
git clone https://github.com/kota-kawa/Marmo-Core.git
cd Marmo-Core
marmo validate examples/resources
marmo search examples/resources --task "read a local text file safely"
```

モデルのアカウントや Python 側の手動設定なしで、同梱の JSON 検証 Tool を実行できます。

```bash
marmo run resources/tools/validate-json.json \
  --task "validate JSON input" \
  --tool-args '{"tool.marmo.samples.validate-json":{"value":{"name":"Marmo"},"schema":{"type":"object","required":["name"],"properties":{"name":{"type":"string"}}}}}' \
  --strict --format json
```

`--tool-args` はモックモデルに呼び出し引数を渡します。モデルに引数を考えさせるものではありません。`resources/` には Memory、Tool、Agent のサンプルが各 10 件あります。Tool と Agent のサンプルには実行できるハンドラがあります。

### 実モデルを使う

作業ディレクトリに `.env` を作るか、同じ変数をシェルで設定します。ソースを取得した場合はテンプレートから始められます。

```bash
cp .env.example .env
```

| プロバイダー | 必要な環境変数 |
| --- | --- |
| OpenAI 互換 | `OPENAI_API_KEY`、`OPENAI_MODEL` |
| Anthropic | `ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL`、`ANTHROPIC_MAX_TOKENS` |

対応する Python プロバイダーのコンストラクタに、モデル名や最大トークン数を明示的に渡すこともできます。OpenAI 互換の別の接続先には `OPENAI_BASE_URL` を設定します。空なら `api.openai.com` が使われます。`OPENAI_REASONING_EFFORT` は任意で、利用可能な値はプロバイダーによって異なります。設定全体と例は [`.env.example`](.env.example) を参照してください。OS の環境変数は `.env` より優先されます。

リポジトリを取得したディレクトリから、OpenAI 互換モデルにファイル操作 Tool を選ばせる例です。

```bash
marmo run resources/tools \
  --llm openai \
  --task "List the text files in the current directory, then read each one and tell me what they say" \
  --granted-permission fs.read \
  --allow-side-effect none --allow-side-effect read
```

Anthropic では `--llm anthropic` を使います。実モデルを選んだ場合、`--tool-args` は無視され、Tool と引数はモデルが選びます。既定の語彙検索はリソースの英語メタデータに照合します。日本語などで目標を書く場合は `--retriever hyde` を付けると、指定した実モデルが検索前に目標をその語彙へ言い換えます。

Python で同等の検索設定を組み立てる例です。

```python
from marmo_core import HydeRetriever, Kernel, LexicalRetriever, OpenAICompatibleLLMProvider, load_registry

llm = OpenAICompatibleLLMProvider()
kernel = Kernel(load_registry(["resources/tools"]), llm, retriever=HydeRetriever(llm, LexicalRetriever()))
```

### 実行時の注意

- `--granted-permission` と `--allow-side-effect` は別々の条件です。後者は値を厳密に照合する繰り返し指定可能な許可リストで、副作用なしと読み取りの両方を許すには、上の例のように両方を指定します。
- `marmo run` の既定はモックモデルです。リソースのスキップ後も処理が続く場合があります。自動化では `--strict` を使うと、スキップ、`--tool-args` に指定した Tool の未評価、利用できるリソースとの不一致を失敗として扱えます。
- POSIX 環境では、import 可能で入出力が JSON 対応の Python Tool ハンドラを `--timeout-mode process` で期限時に停止できます。このモードではローカル関数を実行前に拒否します。Windows では子プロセスの停止を保証できないため process モードを拒否します。既定の `thread` モードは待機時間だけを制限します。timeout 後は外部への副作用が完了した可能性があるため、人が結果を確認してから再実行します。
- Tool の引数が `input_schema` に合わない場合、実モデルに修正を求められます。`--max-input-repairs` の既定は 2 回です。モデルに渡す Tool の出力は、既定で推定 8,000 トークンを上限とします（`--max-tool-output-tokens`）。
- パスを省略した CLI コマンドは、カレントディレクトリの `resources`、`skills`、`examples/resources` を自動検出します。コネクタだけを使う場合は `--no-default-resources` を指定します。
- 同梱のファイル操作サンプルはカレントディレクトリ内を対象にします。外部へ作用するサンプルには、宣言された権限と人の承認が必要です。通知サンプルは環境変数 `MARMO_NOTIFICATION_<DESTINATION>_URL` を読み、`format-code` サンプルには Ruff を含む `.[dev]` が必要です。

CLI の全オプションは `marmo --help` または `marmo run --help` で確認できます。

### 詳しい資料と貢献

| 資料 | 内容 |
| --- | --- |
| [プロジェクトサイト](https://project-kk.com/marmo) | ライブラリの概要、機能、使い方。 |
| [組み込みコネクタ](docs/connectors.md) | コネクタの設定と使い方。 |
| [ローカルリソースパッケージ](docs/local-resource-packages.md) | ローカルリソースの梱包と読み込み。 |
| [ベンチマーク](benchmarks/README.md) | ルーティングの評価と測定結果。 |
| [アーキテクチャ](ARCHITECTURE.md) | カーネルの処理経路と拡張点。 |
| [貢献ガイド](CONTRIBUTING.md) | 開発環境、チェック、PR の手順。 |
| [変更履歴](CHANGELOG.md) | 公開済み・今後の変更。 |

不具合や機能の要望は [GitHub Issues](https://github.com/kota-kawa/Marmo-Core/issues) に報告してください。Marmo-Core は [Apache License 2.0](LICENSE) で配布しています。

</details>
