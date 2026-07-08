"""实时窄表 PriceTick (SPEC §3.6). 时序表 + (node_id, ts DESC) 索引."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin


class PriceTick(Base, TimestampMixin):
    __tablename__ = "price_tick"
    __table_args__ = (
        # (node_id, ts DESC): 取某节点最近序列的核心索引 (SPEC §3.6).
        # SQLite 自动索引方向无法直接指定; Postgres 下 btree 按节点+时间高效区间扫.
        Index("ix_price_tick_node_ts", "node_id", "ts", unique=False),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(16), nullable=False)
    series_type: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    quality_flag: Mapped[str] = mapped_column(String(16), nullable=False, default="OK")
    ingested_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())


__all__ = ["PriceTick"]