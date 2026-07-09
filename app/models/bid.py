"""报价记录 ORM (SPEC §2). 待出清报价队列的持久化形态."""

from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BidRecord(Base, TimestampMixin):
    __tablename__ = "bid"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    unit_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_markup: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    segment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    segments_json: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")


__all__ = ["BidRecord"]
