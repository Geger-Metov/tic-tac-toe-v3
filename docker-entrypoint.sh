#!/bin/sh
set -e

# compose.yaml уже держит старт этого контейнера до готовности БД
# (depends_on: db: condition: service_healthy), так что отдельный
# wait-for-postgres тут не нужен — достаточно прогнать миграции.
echo "Applying database migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn tic_tac_toe.main:app --host 0.0.0.0 --port 8000
