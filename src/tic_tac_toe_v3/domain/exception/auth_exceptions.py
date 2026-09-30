"""
domain-слой не должен знать про HTTP. AuthService/UserService лежат в datasource, 
но по смыслу это всё ещё бизнес-логика, а не веб-логика: она не обязана знать, 
что «неверный пароль» — это именно код 401, а «логин занят» — именно 409. Если 
завтра эти сервисы понадобится переиспользовать не через HTTP (например, в 
CLI-скрипте или grpc), им не придётся тащить с собой fastapi.HTTPException.
"""

class InvalidCredentialsError(Exception):
    """Логин/пароль неверны или отсутствуют — веб-слой превращает это в 401."""
    pass


class UserAlreadyExistsError(Exception):
    """Пользователь с таким логином уже зарегистрирован — веб-слой превращает это в 409."""

    def __init__(self, login: str):
        super().__init__(f"User with login '{login}' already exists")
        self.login = login
