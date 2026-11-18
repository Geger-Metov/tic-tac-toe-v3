"""
Приложение БЕЗ подмены get_db_session: проверяет, что сессия действительно
создаётся из app.state и что commit происходит ДО отправки ответа.

Остальные интеграционные тесты подменяют get_db_session на общую тестовую
транзакцию, поэтому настоящую зависимость (engine, фабрика сессий, commit)
они не проходят вообще. Здесь данные коммитятся по-настоящему, так что тест
сам убирает за собой созданного пользователя.
"""

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from fake_redis import FakeRedis
from tic_tac_toe.infrastructure.persistence.model.user_model import UserModel
from tic_tac_toe.main import create_app


@pytest_asyncio.fixture
async def real_app(fake_redis: FakeRedis):
    app = create_app(redis_client=fake_redis)
    try:
        yield app
    finally:
        # ASGITransport не запускает lifespan, поэтому закрываем engine сами.
        await app.state.engine.dispose()


@pytest_asyncio.fixture
async def real_client(real_app) -> AsyncGenerator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=real_app), base_url="http://test") as ac:
        yield ac


async def test_app_owns_engine_and_sessionmaker(real_app):
    assert real_app.state.engine is not None
    assert real_app.state.sessionmaker is not None


async def test_unknown_login_goes_through_real_session(real_client):
    # Запрос реально ходит в БД (поиск логина) и получает 401, а не 500.
    response = await real_client.post(
        "/auth/login", json={"login": f"nobody-{uuid4().hex}", "password": "whatever1"}
    )

    assert response.status_code == 401


async def test_signup_is_committed_before_response(real_app, real_client):
    login = f"real-session-{uuid4().hex[:12]}"
    try:
        signup = await real_client.post(
            "/auth/signup", json={"login": login, "password": "secret123"}
        )
        assert signup.status_code == 201

        # Вход идёт в новой сессии: пользователь виден, только если signup
        # закоммитился до ответа (scope="function" у DbSession).
        auth = await real_client.post("/auth/login", json={"login": login, "password": "secret123"})
        assert auth.status_code == 200
    finally:
        async with real_app.state.sessionmaker() as session:
            await session.execute(delete(UserModel).where(UserModel.login == login))
            await session.commit()
