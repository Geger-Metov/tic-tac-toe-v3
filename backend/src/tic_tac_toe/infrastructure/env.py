from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    """
    Ищет .env, поднимаясь от расположения ЭТОГО файла вверх, пока не найдёт
    либо сам .env, либо маркер корня репозитория (compose.yaml или .git) — не
    зависим ни от текущей рабочей директории процесса, ни от раскладки (локально
    backend/src/tic_tac_toe, в Docker — плоско /app/tic_tac_toe).

    Единственный .env лежит в КОРНЕ репозитория (рядом с compose.yaml): его же
    читает docker compose, поэтому локальный запуск и compose используют одни
    значения.

    В Docker-образе .env-файла нет (он в .dockerignore, переменные приходят от
    docker compose) — тогда это просто ничего не делает.

    load_dotenv() по умолчанию НЕ перезаписывает уже заданные переменные
    окружения: реальные переменные (compose, shell, тесты) приоритетнее .env.
    Вызывать можно сколько угодно раз — повторная загрузка безвредна.
    """
    current = Path(__file__).resolve().parent
    for _ in range(8):  # разумный предел подъёма
        candidate = current / ".env"
        if candidate.is_file():
            load_dotenv(candidate)
            return
        if (current / "compose.yaml").is_file() or (current / ".git").exists():
            return  # дошли до корня репозитория, .env нет — нормальная ситуация
        current = current.parent
