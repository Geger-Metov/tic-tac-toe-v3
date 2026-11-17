from redis.asyncio import Redis

from tic_tac_toe.domain.exception.auth_exceptions import TooManyLoginAttemptsError


class LoginRateLimiter:
    """
    Защита /auth/login от перебора пароля: для одного логина допускается не
    более max_attempts попыток входа за окно window_seconds без успешного
    входа. Дальше вход под этим логином блокируется до конца окна — даже с
    верным паролем.

    Счётчик — ключ "login_failures:<login>" в Redis, TTL = окно (отсчитывается
    от первой попытки — фиксированное окно). Успешный вход счётчик сбрасывает.

    ПОЧЕМУ ПОПЫТКА СЧИТАЕТСЯ ДО ПРОВЕРКИ ПАРОЛЯ. Схема "прочитать счётчик →
    проверить пароль → увеличить счётчик при неудаче" дырявая: при ста
    одновременных запросах все сто читают счётчик, равный 0, все проходят
    проверку лимита, и все сто получают проверку пароля — лимит не работает
    против параллельного перебора. Поэтому begin_attempt() сначала атомарно
    делает INCR (Redis выполняет команды по одной, так что каждому запросу
    достаётся свой номер попытки) и только по этому номеру решает, пускать ли
    дальше: к проверке пароля доходят максимум max_attempts запросов за окно,
    сколько бы их ни пришло одновременно.

    Осознанные свойства:
      * Попытки блокированных запросов тоже растут в счётчике, но окно они не
        продлевают: TTL ставится один раз, на первой попытке.
      * Считаются и попытки для несуществующих логинов — иначе по тому, что
        блокировка наступает (или нет), можно было бы узнавать, существует ли
        такой пользователь.
      * Ограничение по логину, не по IP: за обратным прокси IP клиента
        ненадёжен. Цена — злоумышленник может нарочно "забить" счётчик чужого
        логина и на время окна заблокировать владельцу вход.
    """

    _PREFIX = "login_failures:"

    def __init__(self, redis: Redis, max_attempts: int, window_seconds: int) -> None:
        self._redis = redis
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds

    async def begin_attempt(self, login: str) -> None:
        """
        Засчитывает попытку входа и кидает TooManyLoginAttemptsError, если это
        уже попытка сверх лимита. Вызывать ДО проверки пароля, один раз на попытку.
        """
        key = self._key(login)
        attempts = await self._redis.incr(key)

        # TTL ставим, если его нет (ttl < 0). INCR и EXPIRE — две команды, и
        # если процесс умрёт между ними, ключ останется без срока жизни и
        # блокировка стала бы вечной. Проверка TTL на каждой попытке это лечит.
        ttl = await self._redis.ttl(key)
        if ttl < 0:
            await self._redis.expire(key, self._window_seconds)
            ttl = self._window_seconds

        if attempts > self._max_attempts:
            raise TooManyLoginAttemptsError(retry_after_seconds=max(ttl, 1))

    async def reset(self, login: str) -> None:
        """Сбрасывает счётчик (после успешного входа)."""
        await self._redis.delete(self._key(login))

    def _key(self, login: str) -> str:
        return f"{self._PREFIX}{login}"
