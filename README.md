# Marmo-Core

[![PyPI](https://img.shields.io/pypi/v/marmo-core.svg)](https://pypi.org/project/marmo-core/)
[![Python versions](https://img.shields.io/pypi/pyversions/marmo-core.svg)](https://pypi.org/project/marmo-core/)
[![CI](https://github.com/kota-kawa/Marmo-Core/actions/workflows/ci.yml/badge.svg)](https://github.com/kota-kawa/Marmo-Core/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Marmo-Core is a lightweight Python kernel for registering, retrieving,
selecting, and safely executing AI-agent resources.

## Requirements

- Python 3.10 or newer

Install the published package with:

```bash
python -m pip install marmo-core
```

For local development, install the checkout with:

```bash
python -m pip install -e '.[dev]'
```

## Quickstart (Python)

Register a tool, let the kernel pick it for a goal, gate it through the
policy layer, and execute it. This runs offline with the deterministic mock
model; swap in `OpenAICompatibleLLMProvider()` or `AnthropicLLMProvider()`
to use a real one.

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
print(result.status, result.output)   # completed Task complete. Tool tool.math.add returned: {"sum": 5}
```

`examples/hello_world.py` is the same program with the audit trail printed;
the other files in `examples/` cover delegation, human approval, planning, and
recovery.

## Quickstart (CLI)

Validate and inspect the bundled resource examples with:

```bash
marmo validate examples/resources
marmo search examples/resources --task "read a local text file safely"
```

The `resources` directory also includes ten standalone samples for each of
Memory, Tool, and Agent. Every Tool and Agent sample resolves an executable
standard-library implementation through its `python:` ref, so no manual
binding is needed. Filesystem samples are confined to the current working
directory. External samples still require the declared permissions and human
approval; notification webhooks are configured through
`MARMO_NOTIFICATION_<DESTINATION>_URL` rather than model-visible arguments.
The `format-code` sample invokes Ruff and therefore requires the `.[dev]`
extra.

```bash
marmo validate resources/memory resources/tools resources/agents
marmo list resources/memory resources/tools resources/agents
```

Run the offline JSON validation Tool end to end with the mock LLM:

```bash
marmo run resources/tools/validate-json.json \
  --task "validate JSON input" \
  --tool-args '{"tool.marmo.samples.validate-json":{"value":{"name":"Marmo"},"schema":{"type":"object","required":["name"],"properties":{"name":{"type":"string"}}}}}' \
  --strict --format json
```

Agent samples are also directly executable:

```bash
marmo run resources/agents/security-reviewer.json \
  --task "review webhook security" \
  --tool-args '{"agent.marmo.samples.security-reviewer":{"goal":"Review webhook security","context":"external upload"}}' \
  --format json
```

## Run with a real model

`marmo run` uses the mock model by default, which replays the arguments given
in `--tool-args`. Pass `--llm openai` or `--llm anthropic` to let a real model
choose and call the tools; the provider reads its key, model, and endpoint
from the environment or `.env` (see the next section) and `--tool-args` is
ignored.

```bash
marmo run resources/tools \
  --llm openai \
  --task "List the text files in the current directory, then read each one and tell me what they say" \
  --granted-permission fs.read \
  --allow-side-effect none --allow-side-effect read
```

Resources are matched to the goal by lexical retrieval over their English
metadata. For goals written in another language, add `--retriever hyde`: the
model first restates the goal in the registry's vocabulary, then retrieval
runs on that restatement.

```bash
marmo run resources/tools \
  --llm openai --retriever hyde \
  --task "カレントディレクトリのテキストファイルを一覧して、それぞれの内容を教えてください" \
  --granted-permission fs.read \
  --allow-side-effect none --allow-side-effect read
```

If retrieval matches nothing, the model answers without tools and the result's
`detail` says so; with `--strict` that is a failure rather than a silent
success. Provider errors are reported with the HTTP status and the API's own
message (for example an unsupported parameter or an invalid model name).

In Python, the same setup is:

```python
from marmo_core import HydeRetriever, Kernel, LexicalRetriever, OpenAICompatibleLLMProvider, load_registry

llm = OpenAICompatibleLLMProvider()          # OPENAI_MODEL / OPENAI_API_KEY / OPENAI_BASE_URL from .env
kernel = Kernel(load_registry(["resources/tools"]), llm, retriever=HydeRetriever(llm, LexicalRetriever()))
```

## API and model configuration

Create a `.env` file and set the relevant key when using an OpenAI-compatible
LLM, Anthropic LLM, or embedding provider. Model names and model-specific
runtime settings are also read from `.env` rather than being hard-coded by
the providers. In a source checkout, `.env.example` can be copied as a
starting point:

```bash
cp .env.example .env
```

```dotenv
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.6-terra
OPENAI_REASONING_EFFORT=none
OPENAI_BASE_URL=
ANTHROPIC_MODEL=claude-sonnet-5
ANTHROPIC_MAX_TOKENS=16384
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

`OPENAI_MODEL`, `ANTHROPIC_MODEL`, and `OPENAI_EMBEDDING_MODEL` are required
when the corresponding provider is constructed without an explicit `model`
argument. `OPENAI_BASE_URL` points `OpenAICompatibleLLMProvider` at any
OpenAI-compatible endpoint; for Groq, set it to
`https://api.groq.com/openai/v1` with `OPENAI_MODEL=openai/gpt-oss-120b` and
the Groq key in `OPENAI_API_KEY`. Leave it empty for `api.openai.com`, where
the provider sends `max_completion_tokens` (current OpenAI models reject
`max_tokens`); other servers get `max_tokens`, and the provider switches once
if the server reports the chosen parameter as unsupported. Tool names are
encoded on the wire because resource ids such as `tool.files.read-text`
contain dots that the OpenAI and Anthropic tool grammars reject; the kernel
and audit log keep seeing the real resource ids. `ANTHROPIC_MAX_TOKENS` is required unless `max_tokens` is passed
explicitly. `OPENAI_REASONING_EFFORT` is optional and applies when the OpenAI
model is resolved from the environment. The package loads `.env` without
overriding values already present in the operating-system environment. `.env`
is excluded from Git.

The benchmark-only embedding and cross-encoder integration is optional:

```bash
python -m pip install '.[benchmark]'
```

Run the test suite with:

```bash
python -W error::ResourceWarning -m unittest discover -s tests
```

## Strict CLI runs

The kernel normally allows a task to recover after a resource is denied or
cannot be activated. For automation and release checks, pass `--strict` so a
skipped resource or a tool named in `--tool-args` that was not evaluated makes
the command exit non-zero.

CLI commands auto-discover `resources`, `skills`, or `examples/resources` from
the current directory when no resource path is provided. Connector-only runs
should pass `--no-default-resources` to make their behavior independent of the
working directory.

`--allow-side-effect` is an exact, repeatable allowlist. For example, allowing
both side-effect-free resources and read operations requires
`--allow-side-effect none --allow-side-effect read`.

See [Built-in Connectors](docs/connectors.md) and
[Local Resource Packages](docs/local-resource-packages.md) for complete usage
examples.
