from datetime import timedelta
from typing import Optional
from uuid import UUID

from redis.asyncio import Redis


class RefreshTokenStore:
    """
    Реестр выпущенных и ещё не использованных refreshToken'ов в Redis
    (раньше — таблица refresh_tokens в Postgres).

    Модель данных: ключ "refresh_token:<jti>" → UUID пользователя, с TTL,
    равным сроку жизни токена. Из этого выходит всё нужное:
      * одноразовость — claim() это GETDEL: "прочитать и удалить" одной
        атомарной командой, так что два параллельных запроса с одним токеном
        не могут оба его получить;
      * очистка — просроченные ключи Redis удаляет сам, ничего не копится;
      * "неизвестный", "уже использованный" и "просроченный" токен выглядят
        одинаково — ключа нет.
    Если Redis потеряет данные (рестарт без персистентности), все выданные
    refreshToken'ы станут недействительными, и пользователям придётся войти
    заново — для учебного проекта допустимо, в compose включён AOF.
    """

    _PREFIX = "refresh_token:"

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def register(self, jti: UUID, user_id: UUID, ttl: timedelta) -> None:
        # max(..., 1): SET ... EX 0 Redis отвергает; токен со сроком < 1 с не бывает смысла хранить.
        await self._redis.set(self._key(jti), str(user_id), ex=max(int(ttl.total_seconds()), 1))

    async def claim(self, jti: UUID) -> Optional[UUID]:
        """UUID владельца, если токен был выпущен, не использован и не просрочен
        (и после этого токен считается использованным); иначе None."""
        value = await self._redis.getdel(self._key(jti))
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode()
        return UUID(value)

    def _key(self, jti: UUID) -> str:
        return f"{self._PREFIX}{jti}"
