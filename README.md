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
python -m pip install .
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
python -m unittest discover -s tests
```
