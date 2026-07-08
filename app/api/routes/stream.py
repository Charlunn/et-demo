"""实时流端点 (SPEC §3.6): GET /stream 模拟推流 (合成数据) + 1h 聚合."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.schemas.market import PriceTick
from scripts.seed_demo import seed_market

router = APIRouter(prefix="/stream", tags=["stream"])

_BASE_TS = datetime(2024, 1, 1, tzinfo=UTC)


@router.get(
    "", response_model=list[PriceTick], summary="实时 tick 模拟推流 (合成数据, 15-min; 生产 5-min)"
)
async def get_stream(
    user: Annotated[dict, Depends(get_current_user)],
    node: str = Query("LOAD", description="节点 ID (REF/LOAD)"),
    series: str = Query("lmp", description="序列类型: lmp / load"),
    span: int = Query(96, ge=1, le=288, description="返回最近多少 tick"),
    aggregate_1h: bool = Query(
        False, description="聚合为 1h 均值 (SQLite 用 strftime 等价 time_bucket)"
    ),
) -> list[PriceTick]:
    m = seed_market(days=max(span // 96 + 1, 1))
    if series == "lmp":
        arr = m.lmp_load_history if node == "LOAD" else m.lmp_ref_history
    elif series == "load":
        arr = m.load_load if node == "LOAD" else m.load_ref
    else:
        arr = m.lmp_load_history
    arr = np.asarray(arr[:span]).ravel()

    if aggregate_1h:
        # 1h = 4 个 15-min; 以 strftime 等价 time_bucket 的口径: 每 4 点取均值.
        agg = np.array([np.mean(arr[i : i + 4]) for i in range(0, len(arr) - 3, 4)])
        step = timedelta(hours=1)
        start = _BASE_TS
        out = [
            PriceTick(
                ts=start + i * step,
                node_id=node,
                series_type=series,
                value=float(v),
                quality_flag="OK",
            )
            for i, v in enumerate(agg)
        ]
    else:
        out = [
            PriceTick(
                ts=_BASE_TS + timedelta(minutes=15 * i),
                node_id=node,
                series_type=series,
                value=float(v),
                quality_flag="OK",
            )
            for i, v in enumerate(arr)
        ]
    return out
