from celery import Celery

from tic_tac_toe.infrastructure.tasks.celery_config import (
    get_broker_url,
    get_cleanup_interval_seconds,
)
from tic_tac_toe.infrastructure.tasks.names import CLEANUP_ABANDONED_GAMES

celery_app = Celery(
    "tic_tac_toe",
    broker=get_broker_url(),
    # Модули с задачами импортируются воркером при старте (а не здесь), иначе
    # cleanup_tasks и celery_app импортировали бы друг друга по кругу.
    include=["tic_tac_toe.infrastructure.tasks.cleanup_tasks"],
)

celery_app.conf.update(
    # JSON вместо pickle: pickle из очереди — это выполнение чужого кода,
    # если кто-то получит доступ к брокеру.
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Результаты задач нам не нужны (очистка ничего не отдаёт вызывающему),
    # поэтому backend результатов не заводим вовсе.
    task_ignore_result=True,
    # Подтверждаем задачу брокеру ПОСЛЕ выполнения, а не до: если воркер умрёт
    # посреди задачи, она вернётся в очередь. Цена — задача может выполниться
    # дважды, поэтому задачи должны быть идемпотентными (наша — да: повторное
    # удаление уже удалённого ничего не делает).
    task_acks_late=True,
    # Воркер берёт по одной задаче вперёд, а не набирает пачку: иначе при
    # acks_late долгая задача держит "забронированные" ею сообщения.
    worker_prefetch_multiplier=1,
    # При старте воркер повторяет подключение к брокеру, пока тот не готов
    # (в Docker RabbitMQ может подняться позже воркера).
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "cleanup-abandoned-games": {
            "task": CLEANUP_ABANDONED_GAMES,
            "schedule": get_cleanup_interval_seconds(),
        },
    },
)
