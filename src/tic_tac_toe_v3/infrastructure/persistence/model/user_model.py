from uuid import UUID, uuid4
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from tic_tac_toe.infrastructure.database.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    # unique=True — на уровне БД гарантирует уникальность логина даже при
    # гонке параллельных запросов регистрации (то, что не покрыть одной
    # только проверкой "такой login уже есть?" в сервисе перед сохранением).
    login: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
