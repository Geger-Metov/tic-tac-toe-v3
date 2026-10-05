from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
from redis.asyncio import Redis

from tic_tac_toe.web.route.game_route import router as game_router
from tic_tac_toe.web.route.auth_route import router as auth_router
from tic_tac_toe.web.route.user_route import router as user_router
from tic_tac_toe.web.route.leaderboard_route import router as leaderboard_router
from tic_tac_toe.di.container import Container

# Схему БД теперь целиком создаёт/версионирует Alembic (см. migrations/ и
# docker-entrypoint.sh, который гоняет "alembic upgrade head" перед стартом
# сервера) — Base.metadata.create_all() здесь больше не нужен и намеренно
# убран, чтобы не было двух источников правды о схеме одновременно.


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # При остановке отдаём соединения Redis (схемой БД тут по-прежнему не занимаемся).
    await app.state.container.close()


def create_app(redis_client: Optional[Redis] = None) -> FastAPI:
    """redis_client нужен тестам (подсовывают in-memory фейк); в обычном
    запуске не передаётся — клиент создаётся по REDIS_URL."""
    app = FastAPI(
        title="Tic-Tac-Toe API",
        description="REST API для игры в крестики-нолики с алгоритмом Минимакс.",
        version="3.4.0",
        docs_url="/docs",        # Интерактивная документация Swagger
        redoc_url="/redoc",      # Альтернативная документация ReDoc
        lifespan=lifespan,
    )
    # Создаём DI-контейнер и сохраняем в состоянии приложения
    container = Container(redis_client=redis_client)
    app.state.container = container
    # Подключаем роутеры с эндпоинтами
    app.include_router(auth_router)
    app.include_router(game_router)
    app.include_router(user_router)
    app.include_router(leaderboard_router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
