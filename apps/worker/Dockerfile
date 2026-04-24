FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY apps/worker/pyproject.toml ./
RUN uv pip install --system .

COPY apps/worker/src/ ./src/

CMD ["python", "-m", "arq", "tracegrade_worker.main.WorkerSettings"]
