"""行情 / 机组端点 (SPEC §5): /market, /units.

GET /market?node=&span=  拉历史/聚合行情 (合成数据).
GET /units                机组清单 + 成本曲线参数.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.domain.units import default_units
from app.schemas.bid import UnitOut
from app.schemas.market import LmpPoint, LoadPoint, MarketView
from scripts.seed_demo import seed_market

router = APIRouter(prefix="", tags=["market", "units"])

_BASE_TS = datetime(2024, 1, 1, tzinfo=UTC)


def _ts(i: int) -> datetime:
    return _BASE_TS + timedelta(minutes=15 * i)


@router.get("/units", response_model=list[UnitOut], summary="报价页列出全部机组 + 成本曲线参数")
async def list_units(user: Annotated[dict, Depends(get_current_user)]) -> list[UnitOut]:
    return [UnitOut(**u.__dict__) for u in default_units()]


@router.get("/market", response_model=MarketView, summary="行情看板: 多节点历史 LMP + 负荷")
async def get_market(
    user: Annotated[dict, Depends(get_current_user)],
    node: str | None = Query(None, description="节点过滤 (REF/LOAD)"),
    span: int = Query(96, ge=1, le=288, description="返回最近多少时段 (15-min 步)"),
) -> MarketView:
    m = seed_market(days=max(span // 96 + 1, 1))
    n = min(span, m.lmp_ref_history.size)
    ref_arr = np.asarray(m.lmp_ref_history[:n]).ravel()
    load_arr = np.asarray(m.lmp_load_history[:n]).ravel()
    nodes = ["REF", "LOAD"] if node is None else [node]
    lmp: list[LmpPoint] = []
    for node_id in nodes:
        arr = ref_arr if node_id == "REF" else load_arr
        for i, v in enumerate(arr):
            lmp.append(LmpPoint(ts=_ts(i), node=node_id, value=float(v)))
    load = [
        LoadPoint(ts=_ts(0), node="REF", value=float(np.mean(m.load_ref[:n]))),
        LoadPoint(ts=_ts(0), node="LOAD", value=float(np.mean(m.load_load[:n]))),
    ]
    # 阻塞标记: 负荷节点 LMP - 参考节点 LMP > 阈值 (出清真实含义的近似, 见出清结果 blocked).
    blocked = [
        i for i in range(min(n, ref_arr.size, load_arr.size)) if (load_arr[i] - ref_arr[i]) > 15.0
    ]
    return MarketView(lmp=lmp, load=load, blocked_periods=blocked)
