import math
import time
from typing import Dict, Optional


class FakeRedis:
    """
    Минимальная in-memory замена redis.asyncio.Redis (с decode_responses=True)
    ровно под те команды, что использует приложение: set/get/getdel/incr/ttl/
    expire/delete. Нужна, чтобы тесты не зависели от запущенного Redis.

    Время управляемое: advance(seconds) "перематывает" часы, поэтому проверка
    TTL не требует sleep(). Поведение команд повторяет настоящий Redis
    (контрактные тесты tests/integration/test_redis_contract.py гоняют одни и
    те же сценарии и против этого фейка, и против реального Redis):
      * SET без EX сбрасывает TTL, INCR его сохраняет;
      * TTL: -2 — ключа нет, -1 — ключ без срока жизни, иначе остаток в секундах.
    """

    def __init__(self) -> None:
        self._data: Dict[str, str] = {}
        self._expires: Dict[str, float] = {}
        self._offset = 0.0

    # ---- время ----------------------------------------------------------

    def _now(self) -> float:
        return time.monotonic() + self._offset

    def advance(self, seconds: float) -> None:
        self._offset += seconds

    def _purge(self, key: str) -> None:
        expires_at = self._expires.get(key)
        if expires_at is not None and expires_at <= self._now():
            self._data.pop(key, None)
            self._expires.pop(key, None)

    # ---- команды --------------------------------------------------------

    async def set(self, name: str, value, ex: Optional[int] = None) -> bool:
        self._data[name] = str(value)
        if ex is not None:
            self._expires[name] = self._now() + ex
        else:
            self._expires.pop(name, None)
        return True

    async def get(self, name: str) -> Optional[str]:
        self._purge(name)
        return self._data.get(name)

    async def getdel(self, name: str) -> Optional[str]:
        self._purge(name)
        self._expires.pop(name, None)
        return self._data.pop(name, None)

    async def incr(self, name: str) -> int:
        self._purge(name)
        value = int(self._data.get(name, "0")) + 1
        self._data[name] = str(value)  # TTL у существующего ключа сохраняется
        return value

    async def ttl(self, name: str) -> int:
        self._purge(name)
        if name not in self._data:
            return -2
        expires_at = self._expires.get(name)
        if expires_at is None:
            return -1
        return max(0, math.ceil(expires_at - self._now()))

    async def expire(self, name: str, seconds: int) -> bool:
        self._purge(name)
        if name not in self._data:
            return False
        self._expires[name] = self._now() + seconds
        return True

    async def delete(self, *names: str) -> int:
        removed = 0
        for name in names:
            self._purge(name)
            if self._data.pop(name, None) is not None:
                removed += 1
            self._expires.pop(name, None)
        return removed

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        pass
