# tic-tac-toe

Крестики-нолики: REST API с компьютерным соперником (Minimax) и веб-клиент.

```
.
├── backend/        FastAPI + SQLAlchemy + PostgreSQL + Redis + Celery (см. backend/README.md)
├── frontend/       React + Vite + TypeScript, раздаётся через nginx (см. frontend/README.md)
├── compose.yaml    весь стек: db, redis, rabbitmq, app, worker, beat, frontend
├── .env.example    переменные окружения (копируется в .env — один на весь репозиторий)
└── .github/        CI (ruff, mypy, pytest, eslint, tsc, сборка), аудит зависимостей, Dependabot
```

## Быстрый старт

```bash
cp .env.example .env
# в .env задай JWT_SECRET_KEY:  openssl rand -hex 32
docker compose up --build
```

Клиент — http://localhost:8080 (порт `FRONTEND_PORT`). nginx раздаёт статику и проксирует
`/api/*` на сервис `app` (префикс `/api` срезается), поэтому браузер работает с одним origin и
CORS не нужен. API напрямую — на `APP_PORT`, документация — `/docs`.

Для разработки с live-reload: `docker compose watch`.

## Разработка по частям

**Бэкенд** (подробности — `backend/README.md`):

```bash
docker compose up -d db redis
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn tic_tac_toe.main:app --reload --app-dir src
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy src
```

**Фронтенд** (бэкенд должен слушать `localhost:8000`):

```bash
cd frontend
pnpm install
pnpm dev          # http://localhost:5173, Vite проксирует /api на localhost:8000
pnpm typecheck && pnpm lint && pnpm build
```

## Проверки

- `pre-commit` (`uv tool install pre-commit && pre-commit install`): ruff, mypy, prettier, запрет коммита `.env`.
- CI (`.github/workflows/ci.yml`): те же проверки + миграции (`alembic upgrade head`, `alembic check`) и тесты с покрытием.
- Аудит зависимостей — отдельный workflow раз в неделю и при изменении lock-файлов.

## Токены и сессия

Клиент хранит токены в `localStorage`; при 401 один раз обновляет пару через `/auth/token/refresh`
(защита от гонок между запросами и вкладками — refresh-токен одноразовый). Идентификатор текущей
партии тоже в `localStorage`: эндпоинта «мои активные игры» пока нет.
