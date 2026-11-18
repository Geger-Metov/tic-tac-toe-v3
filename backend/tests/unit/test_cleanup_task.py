"""
Проводка Celery: задача зарегистрирована, стоит в расписании и вызывает очистку
с настроенным сроком. Сами брокер и воркер здесь не нужны — задача
выполняется локально (Task.apply), а вызов в БД подменён. Тесты синхронные
намеренно: задача сама вызывает asyncio.run(), что нельзя внутри уже
работающего event loop.
"""

from datetime import timedelta

from tic_tac_toe.infrastructure.tasks import cleanup_tasks
from tic_tac_toe.infrastructure.tasks.celery_app import celery_app
from tic_tac_toe.infrastructure.tasks.names import CLEANUP_ABANDONED_GAMES


def test_task_is_registered_under_a_stable_name():
    assert cleanup_tasks.cleanup_abandoned_games.name == CLEANUP_ABANDONED_GAMES


def test_beat_schedules_the_cleanup_task():
    entries = [
        e for e in celery_app.conf.beat_schedule.values() if e["task"] == CLEANUP_ABANDONED_GAMES
    ]

    assert len(entries) == 1
    assert entries[0]["schedule"] > 0


def test_worker_is_configured_for_safe_redelivery():
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_ignore_result is True
    assert celery_app.conf.accept_content == ["json"]


def test_task_runs_cleanup_with_the_configured_max_age(monkeypatch):
    calls = []

    async def fake_cleanup(max_age):
        calls.append(max_age)
        return 3

    monkeypatch.setattr(cleanup_tasks, "_cleanup_abandoned_games", fake_cleanup)
    monkeypatch.setenv("ABANDONED_GAME_MAX_AGE_HOURS", "6")

    result = cleanup_tasks.cleanup_abandoned_games.apply()

    assert result.result == 3
    assert calls == [timedelta(hours=6)]
