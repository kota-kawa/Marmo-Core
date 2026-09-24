# syntax=docker/dockerfile:1
FROM python:3.14-slim

WORKDIR /app

COPY README.md CHANGELOG.md LICENSE pyproject.toml ./
COPY marmo_core ./marmo_core
RUN python3 -m pip install --no-cache-dir .

COPY examples ./examples
COPY resources ./resources
COPY benchmarks/run_evidence_benchmark.py benchmarks/_provenance.py benchmarks/evidence_cases.json ./benchmarks/
COPY scripts ./scripts
COPY tests ./tests

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 marmo
USER marmo

CMD ["python3", "examples/hello_world.py"]
