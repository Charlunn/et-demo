"""时序窄表与聚合 (SPEC §3.6).

- 聚合 view price_1h: Postgres 用 time_bucket('1h', ts); SQLite 无 time_bucket, 用
  strftime('%Y-%m-%d %H:00', ts) 等价实现 (注释标明).
- 保留策略: retention 配置对象 {raw:'30d', rollup_1h:'1y'} + 注释 stub job drop_chunks;
  生产才 create_hypertable (这里仅普通表 + 索引).
- 幂等重灌: bulk insert 支持 ON CONFLICT (node_id,ts) DO UPDATE (Postgres); SQLite 用
  INSERT OR REPLACE — 通过 dialect 判断编译不同语句.

全参数化查询; 无 f-string SQL.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.base import Base  # noqa: F401  (alembic env 引用 Base.metadata)


# 1h 聚合视图: dialect-aware 定义 (Postgres: time_bucket; SQLite: strftime).
PRICE_1H_VIEW_PG = """
CREATE OR REPLACE VIEW price_1h AS
SELECT node_id, series_type,
       time_bucket('1h', ts) AS hour,
       avg(value) AS avg_value, count(*) AS n
FROM price_tick GROUP BY node_id, series_type, time_bucket('1h', ts)
"""

PRICE_1H_VIEW_SQLITE = """
CREATE VIEW IF NOT EXISTS price_1h AS
SELECT node_id, series_type,
       strftime('%Y-%m-%d %H:00', ts) AS hour,
       avg(value) AS avg_value, count(*) AS n
FROM price_tick GROUP BY node_id, series_type, strftime('%Y-%m-%d %H:00', ts)
"""


@dataclass(frozen=True)
class RetentionPolicy:
    """保留策略配置对象 (SPEC §3.6). 生产才真正应用 drop_chunks/hypertable retention."""

    raw: str = "30d"
    rollup_1h: str = "1y"

    def describe(self) -> str:
        return (
            f"retention=(raw:{self.raw}, rollup_1h:{self.rollup_1h}); "
            "stub: 生产才对 hypertable 执行 drop_chunks; 此处仅配置."
        )


RETENTION = RetentionPolicy()


def is_postgres(engine: AsyncEngine) -> bool:
    url = getattr(engine, "url", None)
    if url is None:
        return False
    return str(url).startswith("postgresql")


async def create_price_1h_view(engine: AsyncEngine) -> None:
    """幂等创建 1h 聚合 view (按 dialect 选 time_bucket 或 strftime 等价)."""
    stmt = PRICE_1H_VIEW_PG if is_postgres(engine) else PRICE_1H_VIEW_SQLITE
    async with engine.begin() as conn:
        await conn.execute(text(stmt))


# 幂等批量写 (dialect-aware INSERT OR REPLACE / ON CONFLICT).
def bulk_insert_stmt() -> str:
    # 由调用方据 dialect 选用 (避免在 route 里拼 f-string SQL).
    from app.core.config import settings

    if settings.database_url.startswith("postgres"):
        return (
            "INSERT INTO price_tick (ts, node_id, series_type, value, quality_flag, ingested_at) "
            "VALUES (:ts, :node_id, :series_type, :value, :quality_flag, :ingested_at) "
            "ON CONFLICT (node_id, ts) DO UPDATE SET value=excluded.value"
        )
    return (
        "INSERT OR REPLACE INTO price_tick (ts, node_id, series_type, value, quality_flag, ingested_at) "
        "VALUES (:ts, :node_id, :series_type, :value, :quality_flag, :ingested_at)"
    )


__all__ = [
    "PRICE_1H_VIEW_PG",
    "PRICE_1H_VIEW_SQLITE",
    "RetentionPolicy",
    "RETENTION",
    "create_price_1h_view",
    "bulk_insert_stmt",
]