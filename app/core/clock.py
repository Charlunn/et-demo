"""时钟时间提供者 (SPEC §4.7).

业务不直接 datetime.now(); 经 Depends 注入, 测试可冻结.
"""

from __future__ import annotations

from datetime import datetime, timezone


class Clock:
    """时间提供者. 测试子类覆盖 now() 即可冻结时间."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


def get_clock() -> Clock:
    return Clock()