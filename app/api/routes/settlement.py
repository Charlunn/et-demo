"""结算端点 (SPEC §5): POST /settlement 跑双结算三层."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.security import get_current_user
from app.domain.settlement import CfdContract, settle
from app.schemas.settlement import SettlementBreakdownOut, SettlementRequest

router = APIRouter(prefix="/settlement", tags=["settlement"])


@router.post(
    "",
    response_model=SettlementBreakdownOut,
    status_code=status.HTTP_200_OK,
    summary="跑双结算三层 (日前/实时偏差/中长期差价)",
)
async def post_settlement(
    user: Annotated[dict, Depends(get_current_user)],
    body: SettlementRequest,
) -> SettlementBreakdownOut:
    cfd = None
    if body.cfd is not None:
        cfd = CfdContract(
            strike_price=body.cfd.strike_price,
            quantity=body.cfd.quantity,
            reference_px=body.cfd.reference_px,
        )
    bd = settle(
        s_da=body.s_da,
        s_act=body.s_act,
        lmp_da=body.lmp_da,
        lmp_rt=body.lmp_rt,
        cfd=cfd,
    )
    return SettlementBreakdownOut(da=bd.da, deviation=bd.deviation, cfd=bd.cfd, total=bd.total)
