from redis.asyncio import Redis

from tic_tac_toe.infrastructure.cache.redis_config import get_redis_url


def create_redis_client() -> Redis:
    """
    Один клиент (он же пул соединений) на всё приложение. Соединение
    устанавливается лениво, при первой команде — само создание клиента
    Redis не требует. decode_responses=True: команды возвращают str, а не
    bytes (код хранилищ на это рассчитывает).
    """
    return Redis.from_url(get_redis_url(), decode_responses=True)
