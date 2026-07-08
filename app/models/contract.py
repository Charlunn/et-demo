"""差价合约 (CfD) ORM (SPEC §3.3). 中长期层金融合约持久化."""
from __future__ import annotations

from app.models.base import Base, TimestampMixin
from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column


class Contract(Base, TimestampMixin):
    __tablename__ = "contract"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="cfd")
    strike_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    reference_px: Mapped[float] = mapped_column(Float, nullable=False)


__all__ = ["Contract"]