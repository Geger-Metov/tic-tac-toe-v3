import pytest

from tic_tac_toe.infrastructure.security.jwt_config import get_jwt_secret_key


def test_returns_valid_secret(monkeypatch):
    secret = "a" * 32
    monkeypatch.setenv("JWT_SECRET_KEY", secret)

    assert get_jwt_secret_key() == secret


def test_missing_secret_is_rejected(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="is not set"):
        get_jwt_secret_key()


def test_empty_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "")

    with pytest.raises(RuntimeError, match="is not set"):
        get_jwt_secret_key()


def test_placeholder_from_env_example_is_rejected(monkeypatch):
    # Значение из .env.example достаточно длинное, но заведомо известное.
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-run-openssl-rand-hex-32")

    with pytest.raises(RuntimeError, match="placeholder"):
        get_jwt_secret_key()


def test_short_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 31)

    with pytest.raises(RuntimeError, match="shorter than 32 bytes"):
        get_jwt_secret_key()
