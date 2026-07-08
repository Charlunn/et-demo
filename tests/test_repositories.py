"""仓储测试 (SPEC §6 / P1-3): get_db + 各仓储读写; 用本地 SQLite + alembic 结构.

不跑 alembic (CI 已跑): 这里用 Base.metadata.create_all 在临时库建表是测试一次性手段,
仅验证仓储语义. prod 仍走 alembic (SPEC §4.6).
"""
from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base


@pytest_asyncio.fixture
async def temp_session():
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


# async fixture 需要 asyncio_mode=auto (已在 pyproject 配); 但 fixture 返回 awaitable
# 用 pytest_asyncio.fixture 标注即可. 此处仅验证仓储能写读.
@pytest.mark.asyncio
async def test_bid_repository_roundtrip(temp_session):
    from app.repositories.bid import BidRepository

    repo = BidRepository(temp_session)
    rec = await repo.enqueue("G1", "marginal", 5.0, [{"price": 20.0, "mw": 12.0}])
    assert rec.unit_id == "G1" and rec.segment_count == 1
    items = await repo.list_for_unit("G1")
    assert len(items) == 1 and items[0].strategy == "marginal"


@pytest.mark.asyncio
async def test_clearing_result_repository_save(temp_session):
    from app.repositories.clearing_result import ClearingResultRepository

    repo = ClearingResultRepository(temp_session)
    rec = await repo.save(periods=96, line_flow_limit_mw=80.0, total_cost=1234.0,
                           payload={"status": "optimal"})
    assert rec.periods == 96 and rec.total_cost == 1234.0


@pytest.mark.asyncio
async def test_price_tick_repository_bulk_and_query(temp_session):
    from app.repositories.price_tick import PriceTickRepository
    from app.db.timeseries import bulk_insert_stmt
    from sqlalchemy import text

    # 先建 price_1h view (测试一次性环境里 alembic 没跑, 这里手动建 sqlite 版)
    await temp_session.execute(text(
        "CREATE VIEW IF NOT EXISTS price_1h AS "
        "SELECT node_id, series_type, strftime('%Y-%m-%d %H:00', ts) AS hour, "
        "avg(value) AS avg_value, count(*) AS n "
        "FROM price_tick GROUP BY node_id, series_type, strftime('%Y-%m-%d %H:00', ts)"
    ))
    await temp_session.commit()
    repo = PriceTickRepository(temp_session)
    rows = [
        {"ts": datetime(2024, 1, 1, 0, 0, tzinfo=UTC), "node_id": "LOAD",
         "series_type": "lmp", "value": 40.0, "quality_flag": "OK",
         "ingested_at": datetime(2024, 1, 1, 0, 0, tzinfo=UTC)},
        {"ts": datetime(2024, 1, 1, 0, 15, tzinfo=UTC), "node_id": "LOAD",
         "series_type": "lmp", "value": 42.0, "quality_flag": "OK",
         "ingested_at": datetime(2024, 1, 1, 0, 0, tzinfo=UTC)},
    ]
    n = await repo.bulk_upsert(rows)
    assert n == 2
    got = await repo.latest_for_node("LOAD", "lmp", limit=10)
    assert len(got) == 2 and got[0].series_type == "lmp"
    _ = bulk_insert_stmt  # 验证可获取语句
    hourly = await repo.hourly_avg("LOAD")
    assert len(hourly) == 1 and hourly[0]["n"] == 2
    assert abs(hourly[0]["avg_value"] - 41.0) < 1e-6