FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY apps/api/pyproject.toml ./
RUN uv pip install --system .

COPY apps/api/src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "tracegrade_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
