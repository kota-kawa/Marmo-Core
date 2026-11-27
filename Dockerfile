# syntax=docker/dockerfile:1
FROM python:3.14-slim

WORKDIR /app

COPY README.md CHANGELOG.md LICENSE pyproject.toml ./
COPY marmo_core ./marmo_core
RUN python3 -m pip install --no-cache-dir .

COPY examples ./examples
COPY resources ./resources
# Benchmark modules that the test suite imports, and the fixtures they read.
COPY benchmarks/run_evidence_benchmark.py benchmarks/run_forgery_benchmark.py benchmarks/_provenance.py \
     benchmarks/_claude_cli.py benchmarks/compare_toolret_records.py benchmarks/toolret.py \
     benchmarks/toolret_sae_heldout_ids.json \
     benchmarks/evidence_cases.json benchmarks/set_scenarios.json ./benchmarks/
COPY benchmarks/corpus/set_corpus.json ./benchmarks/corpus/
COPY scripts ./scripts
COPY tests ./tests

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 marmo
USER marmo

CMD ["python3", "examples/hello_world.py"]
