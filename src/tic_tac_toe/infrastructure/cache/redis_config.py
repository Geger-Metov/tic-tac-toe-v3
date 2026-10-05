import os

from tic_tac_toe.infrastructure.env import load_env

load_env()

def get_redis_url() -> str:
    """
    В Docker (compose.yaml) REDIS_URL приходит готовым: redis://redis:6379/0.
    Локально (не в контейнере) собираем из REDIS_HOST/REDIS_PORT — по умолчанию
    localhost:6379, куда compose пробрасывает порт сервиса redis.
    """
    url = os.getenv("REDIS_URL")
    if url:
        return url

    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    return f"redis://{host}:{port}/0"
        