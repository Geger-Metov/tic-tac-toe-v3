import os
from datetime import timedelta

from tic_tac_toe.infrastructure.env import load_env

load_env()


def get_jwt_secret_key() -> str:
    """
    Секрет для подписи JWT. Намеренно нет дефолтного значения (в отличие от
    database/config.py) — использовать угадываемый секрет для подписи токенов
    в реальном окружении значило бы, что любой мог бы подделать чужой
    accessToken. Приложение должно упасть при старте, если секрет не задан,
    а не тихо работать с небезопасным дефолтом.
    """
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY is not set. Add it to your .env "
            "(see .env.example) — without it JWT signing is unsafe."
        )
    # Известное значение из .env.example и короткие секреты позволяют подделать
    # любой токен — отказываемся стартовать, а не работаем молча небезопасно.
    if secret.startswith("change-me") or len(secret.encode()) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY is a placeholder or shorter than 32 bytes. "
            "Generate one: openssl rand -hex 32"
        )
    return secret


def get_access_token_expires() -> timedelta:
    minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    return timedelta(minutes=minutes)


def get_refresh_token_expires() -> timedelta:
    days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    return timedelta(days=days)
