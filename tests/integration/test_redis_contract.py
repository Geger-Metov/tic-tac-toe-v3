"""
Контрактные тесты хранилищ поверх Redis: одни и те же сценарии идут и против
in-memory FakeRedis (на нём построены остальные тесты), и против настоящего
Redis. Так фейк не может незаметно разойтись с реальным поведением команд.
Версия с настоящим Redis пропускается, если он недоступен
(docker compose up -d redis).
"""
import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from fake_redis import FakeRedis
from tic_tac_toe.datasource.repository.refresh_token_store import RefreshTokenStore
from tic_tac_toe.datasource.service.login_rate_limiter import LoginRateLimiter
from tic_tac_toe.domain.exception.auth_exceptions import TooManyLoginAttemptsError
from tic_tac_toe.infrastructure.cache.redis_config import get_redis_url


async def _connect_real() -> Redis:
    client = Redis.from_url(get_redis_url(), decode_responses=True)
    try:
        await client.ping()
    except Exception:
        try:
            await client.aclose()
        except Exception:
            pass
        pytest.skip("Настоящий Redis недоступен (docker compose up -d redis)")
    return client


@pytest_asyncio.fixture(params=["fake", "real"])
async def backend(request):
    """(клиент, pass_time): pass_time(секунды) перематывает время у фейка и
    честно ждёт у настоящего Redis."""
    if request.param == "fake":
        fake = FakeRedis()

        async def pass_time(seconds: float) -> None:
            fake.advance(seconds)

        yield fake, pass_time
    else:
        client = await _connect_real()
        yield client, asyncio.sleep
        await client.aclose()


# ---- RefreshTokenStore -------------------------------------------------------

async def test_claim_succeeds_once(backend):
    client, _ = backend
    store = RefreshTokenStore(client)
    jti, user_id = uuid4(), uuid4()
    await store.register(jti, user_id, timedelta(seconds=60))

    assert await store.claim(jti) == user_id
    assert await store.claim(jti) is None


async def test_claim_unknown_token(backend):
    client, _ = backend

    assert await RefreshTokenStore(client).claim(uuid4()) is None


async def test_token_expires(backend):
    client, pass_time = backend
    store = RefreshTokenStore(client)
    jti = uuid4()
    await store.register(jti, uuid4(), timedelta(seconds=1))

    await pass_time(1.3)

    assert await store.claim(jti) is None


async def test_concurrent_claims_have_exactly_one_winner():
    """Настоящая конкуренция — только против реального Redis: у фейка команды
    не прерываются между собой, гонку он воспроизвести не может."""
    client = await _connect_real()
    try:
        store = RefreshTokenStore(client)
        jti, user_id = uuid4(), uuid4()
        await store.register(jti, user_id, timedelta(seconds=60))

        results = await asyncio.gather(*[store.claim(jti) for _ in range(20)])

        assert [r for r in results if r is not None] == [user_id]
    finally:
        await client.aclose()


# ---- LoginRateLimiter --------------------------------------------------------

def _login() -> str:
    return f"contract_{uuid4()}"


async def test_limiter_blocks_after_max_attempts_then_recovers(backend):
    client, pass_time = backend
    limiter = LoginRateLimiter(client, max_attempts=3, window_seconds=2)
    login = _login()
    for _ in range(3):
        await limiter.begin_attempt(login)  # три попытки допустимы

    with pytest.raises(TooManyLoginAttemptsError) as exc:
        await limiter.begin_attempt(login)  # четвёртая — сверх лимита
    assert 1 <= exc.value.retry_after_seconds <= 2

    await pass_time(2.3)
    await limiter.begin_attempt(login)  # окно истекло


async def test_limiter_reset_clears_counter(backend):
    client, _ = backend
    limiter = LoginRateLimiter(client, max_attempts=2, window_seconds=5)
    login = _login()
    await limiter.begin_attempt(login)
    await limiter.begin_attempt(login)

    await limiter.reset(login)

    await limiter.begin_attempt(login)
    await limiter.begin_attempt(login)
    with pytest.raises(TooManyLoginAttemptsError):
        await limiter.begin_attempt(login)
    await limiter.reset(login)


async def test_limiter_sets_expiry_on_counter(backend):
    client, _ = backend
    limiter = LoginRateLimiter(client, max_attempts=5, window_seconds=5)
    login = _login()

    await limiter.begin_attempt(login)

    assert 0 < await client.ttl(f"login_failures:{login}") <= 5
    await limiter.reset(login)


async def test_limiter_repairs_counter_without_expiry(backend):
    client, _ = backend
    limiter = LoginRateLimiter(client, max_attempts=5, window_seconds=5)
    login = _login()
    key = f"login_failures:{login}"
    await client.set(key, "1")  # ключ без срока жизни, как после сбоя между INCR и EXPIRE
    assert await client.ttl(key) == -1

    await limiter.begin_attempt(login)

    assert 0 < await client.ttl(key) <= 5
    await limiter.reset(login)


async def test_concurrent_attempts_are_capped_at_the_limit():
    """Настоящая конкуренция — только против реального Redis (у фейка команды
    не прерываются). Из 50 одновременных попыток допускается ровно max_attempts."""
    client = await _connect_real()
    login = _login()
    limiter = LoginRateLimiter(client, max_attempts=5, window_seconds=5)
    try:
        results = await asyncio.gather(
            *[limiter.begin_attempt(login) for _ in range(50)], return_exceptions=True
        )

        assert sum(r is None for r in results) == 5
        assert sum(isinstance(r, TooManyLoginAttemptsError) for r in results) == 45
    finally:
        await limiter.reset(login)
        await client.aclose()
