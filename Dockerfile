# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Marmo-Core has no runtime dependencies.  Keeping the source in the image and
# setting PYTHONPATH lets the examples and CLI run without a package install.
COPY marmo_core ./marmo_core
COPY examples ./examples
COPY resources ./resources
COPY tests ./tests
COPY README.md pyproject.toml ./

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 marmo
USER marmo

CMD ["python3", "examples/hello_world.py"]
