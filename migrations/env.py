import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# --- Находим пакет tic_tac_toe и добавляем его родительскую директорию в sys.path.
#
# Это единственное существенное отклонение от того, что генерирует
# "alembic init -t async": там подразумевается, что prepend_sys_path в
# alembic.ini (по умолчанию ".") уже даёт доступ к пакету. У нас так не
# получится сделать одной статической настройкой, потому что пакет лежит в
# разных местах в разных средах:
#   - локально:  <project_root>/src/tic_tac_toe  (см. README: --app-dir src)
#   - в Docker:  /app/tic_tac_toe                 (см. Dockerfile — специально
#     скопирован плоско, без промежуточного src/, чтобы слой с зависимостями
#     не зависел от структуры src/)
# alembic.ini и migrations/ лежат в корне проекта в обоих случаях, поэтому
# ищем от него.
_project_root = Path(__file__).resolve().parent.parent
for _candidate in (_project_root / "src", _project_root):
    if (_candidate / "tic_tac_toe").is_dir():
        sys.path.insert(0, str(_candidate))
        break
else:
    raise RuntimeError(
        "He удалось найти пакет tic_tac_toe ни в <project_root>/src, ни в <project_root>"
    )

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from tic_tac_toe.infrastructure.database.base import Base
from tic_tac_toe.infrastructure.database.config import get_database_url
# Импорт моделей обязателен: только так они регистрируются в Base.metadata,
# и только тогда autogenerate вообще их увидит.
from tic_tac_toe.infrastructure.persistence.model.game_model import GameModel
from tic_tac_toe.infrastructure.persistence.model.user_model import UserModel

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # В alembic.ini сознательно нет строки "sqlalchemy.url" (см. комментарий
    # там же), поэтому здесь, в отличие от дефолтного шаблона, берём URL из
    # той же функции, что использует само приложение, а не из config.
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    configuration = config.get_section(config.config_ini_section, {})
    # Единая точка правды для URL БД — та же, что у приложения
    # (tic_tac_toe.infrastructure.database.config, переменная DATABASE_URL).
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
