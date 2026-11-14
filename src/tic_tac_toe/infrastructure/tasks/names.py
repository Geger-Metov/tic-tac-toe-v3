# Имена задач Celery — отдельным модулем, чтобы расписание (celery_app) и сама
# задача (cleanup_tasks) ссылались на одну константу и не расходились.
CLEANUP_ABANDONED_GAMES = "games.cleanup_abandoned"
