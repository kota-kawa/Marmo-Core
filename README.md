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

## OpenAI API key

Create a `.env` file and set the key when using an OpenAI-compatible LLM or
embedding provider. In a source checkout, `.env.example` can be copied as a
starting point:

```bash
cp .env.example .env
```

```dotenv
OPENAI_API_KEY=your_key_here
```

The package loads `.env` without overriding an existing `OPENAI_API_KEY` in
the operating-system environment. `.env` is excluded from Git.

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
