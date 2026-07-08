"""PriceTick 仓储 (SPEC §2 repositories). DB 访问唯一去处; 全参数化查询."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.timeseries import bulk_insert_stmt
from app.models.price_tick import PriceTick


class PriceTickRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """幂等批量写. 使用 dialect-aware 语句 (spec §3.6). 返回写入行数."""
        if not rows:
            return 0
        stmt = text(bulk_insert_stmt())
        await self._session.execute(stmt, rows)
        await self._session.commit()
        return len(rows)

    async def latest_for_node(self, node_id: str, series_type: str, limit: int = 288) -> list[PriceTick]:
        stmt = (
            select(PriceTick)
            .where(PriceTick.node_id == node_id, PriceTick.series_type == series_type)
            .order_by(PriceTick.ts.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def hourly_avg(self, node_id: str) -> list[dict]:
        """经 price_1h view 取 1h 聚合 (SQLite 等价 time_bucket 已建为 view)."""
        stmt = text("SELECT hour, avg_value, n FROM price_1h WHERE node_id = :n ORDER BY hour")
        result = await self._session.execute(stmt, {"n": node_id})
        return [dict(r._mapping) for r in result.all()]


__all__ = ["PriceTickRepository"]