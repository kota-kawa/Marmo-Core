# Marmo-Core

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
ANTHROPIC_MODEL=claude-sonnet-5
ANTHROPIC_MAX_TOKENS=16384
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

`OPENAI_MODEL`, `ANTHROPIC_MODEL`, and `OPENAI_EMBEDDING_MODEL` are required
when the corresponding provider is constructed without an explicit `model`
argument. `ANTHROPIC_MAX_TOKENS` is required unless `max_tokens` is passed
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
