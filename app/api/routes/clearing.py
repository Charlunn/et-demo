"""出清端点 (SPEC §5): POST /clearing 跑日前联合出清."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.core.ratelimit import limiter
from app.core.security import get_current_user
from app.domain.units import default_network, default_units
from app.schemas.clearing import ClearingRequest, ClearingResultOut, PeriodResultOut
from app.services.clearing import ClearingRequestDTO, run_clearing
from scripts.seed_demo import seed_market

router = APIRouter(prefix="/clearing", tags=["clearing"])


@router.post(
    "",
    response_model=ClearingResultOut,
    status_code=status.HTTP_200_OK,
    summary="跑日前出清 (能量+旋转备用 联合 LP), 返回节点 LMP(能量/阻塞/损耗) + 机组 P/R",
)
@limiter.limit("10/minute")
async def post_clearing(
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
    body: ClearingRequest,
) -> ClearingResultOut:
    m = seed_market(days=body.days, line_flow_limit_mw=body.line_flow_limit_mw)
    units = default_units()
    net = default_network(body.line_flow_limit_mw)
    periods = body.periods
    if body.use_seed and (not body.load_ref or len(body.load_ref) < periods):
        load_ref = m.load_ref[:periods].tolist()
        load_load = m.load_load[:periods].tolist()
        reserve = m.reserve_req[:periods].tolist()
    else:
        load_ref = list(body.load_ref)
        load_load = list(body.load_load)
        reserve = body.reserve_requirement_mw or [0.0] * periods
        if len(load_ref) < periods or len(load_load) < periods:
            from app.core.errors import BusinessValidationError

            raise BusinessValidationError("load_ref/load_load 长度需 >= periods")
    req = ClearingRequestDTO(
        units=units,
        network=net,
        load_per_node={"REF": load_ref, "LOAD": load_load},
        reserve_requirement_mw=reserve,
        periods=periods,
    )
    res = run_clearing(req)
    return ClearingResultOut(
        status=res.status,
        total_cost=res.total_cost,
        periods=[
            PeriodResultOut(
                period=pr.period,
                p=pr.p,
                r=pr.r,
                lmp=pr.lmp,
                lmp_components=pr.lmp_components,
                line_flow_mw=pr.line_flow_mw,
                blocked=pr.blocked,
            )
            for pr in res.periods
        ],
    )
