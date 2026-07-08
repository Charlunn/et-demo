"""SQLAlchemy 2.0 ORM 基类 + 时间戳 mixin (SPEC §2 models/)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """所有 ORM 模型的 declarative 基类."""

    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """created_at / updated_at: 服务端默认值 + onupdate 自动更新."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), default=_utcnow, onupdate=func.now()
    )


__all__: list[Any] = ["Base", "TimestampMixin"]