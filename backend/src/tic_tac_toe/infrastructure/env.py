from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    """
    Ищет .env, поднимаясь от расположения ЭТОГО файла вверх, пока не найдёт
    либо сам .env, либо маркер корня проекта (pyproject.toml) — тот же приём,
    что в migrations/env.py и tests/conftest.py: не зависим ни от текущей
    рабочей директории процесса, ни от раскладки (локально src/tic_tac_toe,
    в Docker — плоско /app/tic_tac_toe).

    В Docker-образе .env-файла обычно нет (он в .dockerignore, переменные
    приходят от docker compose) — тогда это просто ничего не делает.

    load_dotenv() по умолчанию НЕ перезаписывает уже заданные переменные
    окружения: реальные переменные (compose, shell, тесты) приоритетнее .env.
    Вызывать можно сколько угодно раз — повторная загрузка безвредна.
    """
    current = Path(__file__).resolve().parent
    for _ in range(6):  # разумный предел подъёма
        candidate = current / ".env"
        if candidate.is_file():
            load_dotenv(candidate)
            return
        if (current / "pyproject.toml").is_file():
            return  # дошли до корня проекта, .env нет — нормальная ситуация
        current = current.parent
