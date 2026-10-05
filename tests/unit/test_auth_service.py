import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from tic_tac_toe.datasource.repository.refresh_token_store import RefreshTokenStore
from tic_tac_toe.datasource.service.auth_service_impl import AuthService
from tic_tac_toe.datasource.service.jwt_provider_impl import JwtProvider
from tic_tac_toe.datasource.service.login_rate_limiter import LoginRateLimiter
from tic_tac_toe.domain.exception.auth_exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    TooManyLoginAttemptsError,
)
from tic_tac_toe.domain.model.user import User

REFRESH_EXPIRES = timedelta(days=30)


class FakeUserService:
    def __init__(self):
        self.users = {}

    def add(self, login, password):
        user = User(id=uuid4(), login=login, password_hash=password)  # "хэш" = сам пароль, для теста
        self.users[user.id] = user
        return user

    async def register(self, login, password):
        return self.add(login, password)

    async def get_by_login(self, login):
        return next((u for u in self.users.values() if u.login == login), None)

    async def get_by_id(self, id):
        return self.users.get(id)

    def verify_password(self, user, password):
        return user.password_hash == password


def make_provider(access=timedelta(minutes=15), refresh=REFRESH_EXPIRES):
    return JwtProvider("unit-test-secret-key-0123456789-abcdef", access, refresh)


def build_service(users, redis, provider=None):
    return AuthService(
        users,
        provider or make_provider(),
        RefreshTokenStore(redis),
        LoginRateLimiter(redis, max_attempts=5, window_seconds=60),
        REFRESH_EXPIRES,
    )


@pytest.fixture
def users():
    return FakeUserService()


@pytest.fixture
def service(users, fake_redis):
    return build_service(users, fake_redis)


async def fail_login(service, login, times, password="wrong-password"):
    for _ in range(times):
        with pytest.raises(InvalidCredentialsError):
            await service.authenticate(login, password)


# ---- токены ----------------------------------------------------------------

async def test_authenticate_returns_working_pair(service, users):
    user = users.add("alice", "secret123")

    access, refresh = await service.authenticate("alice", "secret123")

    assert await service.get_user_id_from_access_token(access) == user.id
    assert refresh != access


async def test_authenticate_wrong_password(service, users):
    users.add("alice", "secret123")

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("alice", "nope")


async def test_refresh_token_not_accepted_as_access(service, users):
    users.add("alice", "secret123")
    _, refresh = await service.authenticate("alice", "secret123")

    with pytest.raises(InvalidTokenError):
        await service.get_user_id_from_access_token(refresh)


async def test_refresh_is_single_use(service, users):
    users.add("alice", "secret123")
    _, refresh = await service.authenticate("alice", "secret123")

    await service.refresh_access_token(refresh)

    with pytest.raises(InvalidTokenError):
        await service.refresh_access_token(refresh)
    with pytest.raises(InvalidTokenError):
        await service.refresh_refresh_token(refresh)


async def test_rotation_chain_works(service, users):
    users.add("alice", "secret123")
    _, refresh = await service.authenticate("alice", "secret123")

    _, refresh2 = await service.refresh_refresh_token(refresh)
    _, refresh3 = await service.refresh_access_token(refresh2)

    assert len({refresh, refresh2, refresh3}) == 3


async def test_unknown_refresh_token_rejected(users, fake_redis):
    # валидный по подписи refresh, но выпущенный "мимо" хранилища
    provider = make_provider()
    user = users.add("alice", "secret123")
    service = build_service(users, fake_redis, provider)

    with pytest.raises(InvalidTokenError):
        await service.refresh_access_token(provider.generate_refresh_token(user))


async def test_expired_access_token_rejected(users, fake_redis):
    service = build_service(users, fake_redis, make_provider(access=timedelta(seconds=-1)))
    users.add("alice", "secret123")

    access, _ = await service.authenticate("alice", "secret123")

    with pytest.raises(InvalidTokenError):
        await service.get_user_id_from_access_token(access)


async def test_token_signed_with_other_secret_rejected(service, users):
    users.add("alice", "secret123")
    other = JwtProvider("another-unit-test-secret-9876543210-fedcba", timedelta(minutes=15), REFRESH_EXPIRES)
    forged = other.generate_access_token(next(iter(users.users.values())))

    with pytest.raises(InvalidTokenError):
        await service.get_user_id_from_access_token(forged)


# ---- refresh-токены в Redis ------------------------------------------------

def refresh_key(token):
    return f"refresh_token:{UUID(make_provider().get_jti(token))}"


async def test_refresh_token_is_stored_with_ttl_of_its_lifetime(service, users, fake_redis):
    users.add("alice", "secret123")

    _, refresh = await service.authenticate("alice", "secret123")

    ttl = await fake_redis.ttl(refresh_key(refresh))
    assert 0 < ttl <= int(REFRESH_EXPIRES.total_seconds())


async def test_claimed_refresh_token_disappears_from_store(service, users, fake_redis):
    users.add("alice", "secret123")
    _, refresh = await service.authenticate("alice", "secret123")
    key = refresh_key(refresh)
    assert await fake_redis.get(key) is not None

    await service.refresh_access_token(refresh)

    assert await fake_redis.get(key) is None


async def test_refresh_rejected_after_store_ttl_expires(service, users, fake_redis):
    users.add("alice", "secret123")
    _, refresh = await service.authenticate("alice", "secret123")

    # JWT по своим часам ещё действителен, но запись в Redis уже истекла
    fake_redis.advance(REFRESH_EXPIRES.total_seconds() + 1)

    with pytest.raises(InvalidTokenError):
        await service.refresh_access_token(refresh)


# ---- защита логина от перебора --------------------------------------------

async def test_login_locks_after_max_failures_even_with_correct_password(service, users):
    users.add("alice", "secret123")
    await fail_login(service, "alice", 5)

    with pytest.raises(TooManyLoginAttemptsError) as exc:
        await service.authenticate("alice", "secret123")

    assert 1 <= exc.value.retry_after_seconds <= 60


async def test_login_below_limit_is_not_blocked(service, users):
    users.add("alice", "secret123")
    await fail_login(service, "alice", 4)

    access, _ = await service.authenticate("alice", "secret123")

    assert access


async def test_login_unlocks_after_window(service, users, fake_redis):
    users.add("alice", "secret123")
    await fail_login(service, "alice", 5)

    fake_redis.advance(61)

    access, _ = await service.authenticate("alice", "secret123")
    assert access


async def test_successful_login_resets_failure_counter(service, users):
    users.add("alice", "secret123")
    await fail_login(service, "alice", 4)
    await service.authenticate("alice", "secret123")  # сброс счётчика

    await fail_login(service, "alice", 4)  # снова 4 неудачи — до блокировки не дошло

    access, _ = await service.authenticate("alice", "secret123")
    assert access


async def test_unknown_login_is_limited_too(service):
    """Иначе по тому, наступает ли блокировка, можно было бы узнавать,
    существует ли такой пользователь."""
    await fail_login(service, "ghost", 5)

    with pytest.raises(TooManyLoginAttemptsError):
        await service.authenticate("ghost", "whatever")


async def test_lock_is_per_login(service, users):
    users.add("alice", "secret123")
    users.add("bob", "secret456")
    await fail_login(service, "alice", 5)

    access, _ = await service.authenticate("bob", "secret456")

    assert access


async def test_failure_counter_without_ttl_gets_expiry(fake_redis):
    """Если процесс умер между INCR и EXPIRE, ключ остался бы без срока жизни
    и блокировка стала бы вечной — следующая неудача должна это починить."""
    limiter = LoginRateLimiter(fake_redis, max_attempts=5, window_seconds=60)
    await fake_redis.set("login_failures:alice", "1")  # без EX
    assert await fake_redis.ttl("login_failures:alice") == -1

    await limiter.begin_attempt("alice")

    assert 0 < await fake_redis.ttl("login_failures:alice") <= 60


async def test_blocked_attempts_do_not_extend_the_lock(service, users, fake_redis):
    """Окно отсчитывается от первой попытки: настойчивые попытки во время
    блокировки её не продлевают."""
    users.add("alice", "secret123")
    await fail_login(service, "alice", 5)

    fake_redis.advance(30)
    with pytest.raises(TooManyLoginAttemptsError):
        await service.authenticate("alice", "secret123")  # заблокированная попытка
    fake_redis.advance(31)  # с первой попытки прошло 61 с

    access, _ = await service.authenticate("alice", "secret123")
    assert access


# ---- гонка: параллельные попытки не обходят лимит ----------------------------

class InterleavingUserService(FakeUserService):
    """Отдаёт управление при поиске пользователя, чтобы параллельные запросы
    гарантированно перемешались, и считает реальные проверки пароля."""

    def __init__(self):
        super().__init__()
        self.password_checks = 0

    async def get_by_login(self, login):
        await asyncio.sleep(0)
        return await super().get_by_login(login)

    def verify_password(self, user, password):
        self.password_checks += 1
        return super().verify_password(user, password)


async def test_concurrent_attempts_cannot_exceed_the_limit(fake_redis):
    """
    Регрессия на гонку: схема "прочитать счётчик → проверить пароль → записать
    неудачу" пропускала к проверке пароля ВСЕ одновременные запросы (все читали
    счётчик 0). Попытка должна засчитываться до проверки, поэтому из 20
    параллельных запросов пароль проверяется ровно 5 раз, остальные получают отказ.
    """
    users = InterleavingUserService()
    users.add("alice", "secret123")
    service = build_service(users, fake_redis)

    results = await asyncio.gather(
        *[service.authenticate("alice", "wrong-password") for _ in range(20)],
        return_exceptions=True,
    )

    assert users.password_checks == 5
    assert sum(isinstance(r, InvalidCredentialsError) for r in results) == 5
    assert sum(isinstance(r, TooManyLoginAttemptsError) for r in results) == 15
