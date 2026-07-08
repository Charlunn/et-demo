"""异步 DB 引擎 + get_db 会话 (SPEC §4.6).

get_db yield 且异常时 rollback. 生产用 Postgres, 本地/测试用 SQLite+aiosqlite.
check_db 健康探针用.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            future=True,
            echo=False,
            # SQLite 文件库要求单写连接; aiosqlite 连接池在 sqlite 下需禁用.
            pool_size=5 if not settings.database_url.startswith("sqlite") else 0,
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_maker


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """会话 yield; 异常时 rollback. 用于路由 Depends 替代形式不可用时直接 async-with."""
    session = get_session_maker()()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def check_db() -> None:
    """就绪探针: 执行一次轻量连接校验 (SELECT 1)."""
    from sqlalchemy import text

    async with get_db() as session:
        await session.execute(text("SELECT 1"))


async def dispose_engine() -> None:
    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
        log.info("db_engine_disposed")
    _engine = None
    _session_maker = None


__all__: list[Any] = ["get_engine", "get_session_maker", "get_db", "check_db", "dispose_engine"]