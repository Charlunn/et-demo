"""出清结果 ORM (SPEC §2). 单次出清产物的持久化形态."""
from __future__ import annotations

from app.models.base import Base, TimestampMixin
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class ClearingResultRecord(Base, TimestampMixin):
    __tablename__ = "clearing_result"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    periods: Mapped[int] = mapped_column(Integer, nullable=False)
    line_flow_limit_mw: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="optimal")
    payload_json: Mapped[str] = mapped_column(String, nullable=False)


__all__ = ["ClearingResultRecord"]