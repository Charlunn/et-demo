"""出清结果仓储 (SPEC §2)."""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base  # noqa: F401
from app.models.clearing_result import ClearingResultRecord


class ClearingResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self, periods: int, line_flow_limit_mw: float, total_cost: float, payload: dict
    ) -> ClearingResultRecord:
        rec = ClearingResultRecord(
            periods=periods,
            line_flow_limit_mw=line_flow_limit_mw,
            total_cost=total_cost,
            status="optimal",
            payload_json=json.dumps(payload),
        )
        self._session.add(rec)
        await self._session.commit()
        await self._session.refresh(rec)
        return rec


__all__ = ["ClearingResultRepository"]
