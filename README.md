# Marmo-Core

Marmo-Core is a zero-runtime-dependency Python kernel for registering,
retrieving, selecting, and safely executing AI-agent resources.

## Requirements

- Python 3.10 or newer

Install the package locally with:

```bash
python -m pip install .
```

The benchmark-only embedding and cross-encoder integration is optional:

```bash
python -m pip install '.[benchmark]'
```

Run the test suite with:

```bash
python -m unittest discover -s tests
```
