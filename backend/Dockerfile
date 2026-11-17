FROM python:3.15-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Зависимости: слой пересобирается только при смене pyproject.toml / uv.lock.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-dev


FROM python:3.15-slim

# Тот же базовый образ, что и в build: venv ссылается на его интерпретатор.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --system --no-create-home app
WORKDIR /app

COPY --from=build /app/.venv ./.venv
COPY src/tic_tac_toe ./tic_tac_toe/
COPY alembic.ini ./
COPY migrations ./migrations/
COPY --chmod=755 docker-entrypoint.sh ./

USER app
EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
