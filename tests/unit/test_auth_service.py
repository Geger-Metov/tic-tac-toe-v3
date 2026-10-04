from datetime import timedelta
from uuid import uuid4

import pytest

from tic_tac_toe.datasource.service.auth_service_impl import AuthService
from tic_tac_toe.datasource.service.jwt_provider_impl import JwtProvider
from tic_tac_toe.domain.exception.auth_exceptions import InvalidCredentialsError, InvalidTokenError
from tic_tac_toe.domain.model.user import User


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


class FakeRefreshRepo:
    def __init__(self):
        self.store = {}

    async def save(self, record):
        self.store[record.jti] = record

    async def find_by_jti(self, jti):
        return self.store.get(jti)

    async def mark_used_if_unused(self, jti):
        record = self.store.get(jti)
        if record is None or record.used:
            return False
        record.used = True
        return True


class LosingRaceRefreshRepo(FakeRefreshRepo):
    """Токен выглядит неиспользованным при чтении, но к моменту захвата его
    уже забрал параллельный запрос — захват возвращает False."""

    async def mark_used_if_unused(self, jti):
        self.store[jti].used = True
        return False


def make_provider(access=timedelta(minutes=15), refresh=timedelta(days=30)):
    return JwtProvider("unit-test-secret-key-0123456789-abcdef", access, refresh)


@pytest.fixture
def users():
    return FakeUserService()


@pytest.fixture
def service(users):
    return AuthService(users, make_provider(), FakeRefreshRepo(), timedelta(days=30))


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


async def test_unknown_refresh_token_rejected(users):
    # валидный по подписи refresh, но выпущенный "мимо" репозитория
    provider = make_provider()
    user = users.add("alice", "secret123")
    service = AuthService(users, provider, FakeRefreshRepo(), timedelta(days=30))

    with pytest.raises(InvalidTokenError):
        await service.refresh_access_token(provider.generate_refresh_token(user))


async def test_expired_access_token_rejected(users):
    provider = make_provider(access=timedelta(seconds=-1))
    service = AuthService(users, provider, FakeRefreshRepo(), timedelta(days=30))
    users.add("alice", "secret123")

    access, _ = await service.authenticate("alice", "secret123")

    with pytest.raises(InvalidTokenError):
        await service.get_user_id_from_access_token(access)


async def test_token_signed_with_other_secret_rejected(service, users):
    users.add("alice", "secret123")
    other = JwtProvider("another-unit-test-secret-9876543210-fedcba", timedelta(minutes=15), timedelta(days=30))
    forged = other.generate_access_token(next(iter(users.users.values())))

    with pytest.raises(InvalidTokenError):
        await service.get_user_id_from_access_token(forged)


async def test_losing_the_refresh_race_issues_no_tokens(users):
    repo = LosingRaceRefreshRepo()
    service = AuthService(users, make_provider(), repo, timedelta(days=30))
    users.add("alice", "secret123")
    _, refresh = await service.authenticate("alice", "secret123")
    records_before = len(repo.store)

    with pytest.raises(InvalidTokenError):
        await service.refresh_access_token(refresh)

    assert len(repo.store) == records_before  # новая пара не выдавалась и не регистрировалась
