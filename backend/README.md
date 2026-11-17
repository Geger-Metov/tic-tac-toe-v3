# tic-tac-toe

Крестики-нолики: REST API с компьютерным соперником (Minimax) и веб-клиент.

```
.
├── backend/        FastAPI + SQLAlchemy + PostgreSQL + Redis + Celery (см. backend/README.md)
├── frontend/       React + Vite + TypeScript, раздаётся через nginx
├── compose.yaml    весь стек: db, redis, rabbitmq, app, worker, beat, frontend
└── .env.example    переменные окружения (копируется в .env — один на весь репозиторий)
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
```

**Фронтенд** (бэкенд должен слушать `localhost:8000`):

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, Vite проксирует /api на localhost:8000
npm run build      # проверка типов + сборка
```

Токены клиент хранит в `localStorage`; при 401 один раз обновляет пару через
`/auth/token/refresh` (защита от гонок между запросами и вкладками — refresh-токен одноразовый).
Идентификатор текущей партии тоже в `localStorage`: эндпоинта «мои активные игры» пока нет.
