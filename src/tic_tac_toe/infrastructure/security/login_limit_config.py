import os

from tic_tac_toe.infrastructure.env import load_env

load_env()


def get_login_max_attempts() -> int:
    """Сколько неудачных попыток входа подряд допускается в окне."""
    return int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))


def get_login_window_seconds() -> int:
    """Длина окна подсчёта неудачных попыток (и срок блокировки), секунды."""
    return int(os.getenv("LOGIN_ATTEMPT_WINDOW_SECONDS", "60"))
