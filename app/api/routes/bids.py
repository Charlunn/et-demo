"""报价端点 (SPEC §5): 提交报价 (用策略生成, 不让前端手填 JSON) / 拿报价曲线."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.core.ratelimit import limiter
from app.core.security import get_current_user
from app.domain.units import default_units
from app.schemas.bid import BidCurveOut, BidSegmentOut, BidSubmit
from app.services.bidding import build_bid_curve

log = get_logger(__name__)
router = APIRouter(prefix="/bids", tags=["bids"])

# 待出清报价队列 (进程内). P1-3 接 repositories 后可替换为持久化存储.
_bid_queue: list[BidCurveOut] = []


def _find_unit(unit_id: str):
    for u in default_units():
        if u.unit_id == unit_id:
            return u
    raise NotFoundError(f"未找到机组: {unit_id}")


@router.post(
    "",
    response_model=BidCurveOut,
    status_code=status.HTTP_201_CREATED,
    summary="用策略生成分段报价 (≤10段); 不接受前端手填 JSON",
)
@limiter.limit("10/minute")
async def submit_bid(
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
    body: BidSubmit,
) -> BidCurveOut:
    unit = _find_unit(body.unit_id)
    curve = build_bid_curve(
        unit,
        strategy=body.strategy,
        risk_markup=body.risk_markup,
        forecast_lmp=body.forecast_lmp,
        period=0,
    )
    out = BidCurveOut(
        unit_id=curve.unit_id,
        period=curve.period,
        strategy=curve.strategy,
        segments=[BidSegmentOut(price=s.price, mw=s.mw) for s in curve.segments],
        segment_count=curve.segment_count,
    )
    _bid_queue.append(out)
    log.info(
        "bid_submitted", unit_id=body.unit_id, strategy=body.strategy, segments=curve.segment_count
    )
    return out


@router.get("", response_model=list[BidCurveOut], summary="取该机组待出清报价队列")
async def list_bids(
    user: Annotated[dict, Depends(get_current_user)],
    unit_id: str = Query(..., description="机组 ID"),
) -> list[BidCurveOut]:
    return [b for b in _bid_queue if b.unit_id == unit_id]
