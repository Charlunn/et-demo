"""报价仓储 (SPEC §2). 待出清报价持久化队列."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid import BidRecord


class BidRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, unit_id: str, strategy: str, risk_markup: float,
                      segments: list[dict]) -> BidRecord:
        rec = BidRecord(
            unit_id=unit_id, strategy=strategy, risk_markup=risk_markup,
            segment_count=len(segments), segments_json=json.dumps(segments), status="queued",
        )
        self._session.add(rec)
        await self._session.commit()
        await self._session.refresh(rec)
        return rec

    async def list_for_unit(self, unit_id: str) -> list[BidRecord]:
        stmt = select(BidRecord).where(BidRecord.unit_id == unit_id).order_by(BidRecord.id.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


__all__ = ["BidRepository"]