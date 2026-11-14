import os
from datetime import timedelta
from urllib.parse import quote

from tic_tac_toe.infrastructure.env import load_env

load_env()


def get_broker_url() -> str:
    """
    Адрес брокера сообщений (RabbitMQ). В Docker CELERY_BROKER_URL приходит
    готовым из compose; локально собираем из RABBITMQ_* (по умолчанию
    localhost:5672, куда compose пробрасывает порт). Логин и пароль
    экранируем: спецсимволы в них иначе сломали бы URL.

    Дефолтные ttt/ttt совпадают с compose.yaml, а не с guest/guest: у
    стандартного пользователя guest RabbitMQ разрешает вход только с
    localhost, из соседнего контейнера он не подключится.
    """
    url = os.getenv("CELERY_BROKER_URL")
    if url:
        return url

    user = quote(os.getenv("RABBITMQ_USER", "ttt"), safe="")
    password = quote(os.getenv("RABBITMQ_PASSWORD", "ttt"), safe="")
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = os.getenv("RABBITMQ_PORT", "5672")
    return f"amqp://{user}:{password}@{host}:{port}//"


def get_abandoned_game_max_age() -> timedelta:
    """Игра, в которую за это время никто не присоединился, считается брошенной."""
    return timedelta(hours=float(os.getenv("ABANDONED_GAME_MAX_AGE_HOURS", "24")))


def get_cleanup_interval_seconds() -> float:
    """Как часто beat запускает очистку."""
    return float(os.getenv("CLEANUP_INTERVAL_MINUTES", "60")) * 60
