"""回测端点 (SPEC §5): POST /backtest — 受 scope:backtest:run 保护."""

from __future__ import annotations

from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, Request, status

from app.core.ratelimit import limiter
from app.core.security import require_scope
from app.domain.settlement import CfdContract
from app.domain.units import default_network, default_units
from app.schemas.backtest import BacktestReportOut, BacktestRequest, StrategyReportOut
from app.services.backtest import run_backtest
from app.services.clearing import ClearingRequestDTO
from scripts.seed_demo import seed_market

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post(
    "",
    response_model=BacktestReportOut,
    status_code=status.HTTP_200_OK,
    summary="跑两条策略回测并产 BacktestReport (受 scope:backtest:run 保护)",
)
@limiter.limit("5/minute")
async def post_backtest(
    request: Request,
    user: Annotated[dict, Depends(require_scope("backtest:run"))],
    body: BacktestRequest,
) -> BacktestReportOut:
    m = seed_market(days=body.days, line_flow_limit_mw=body.line_flow_limit_mw)
    units = default_units()
    net = default_network(body.line_flow_limit_mw)
    periods = body.days * 96
    req = ClearingRequestDTO(
        units=units,
        network=net,
        load_per_node={
            "REF": m.load_ref[:periods].tolist(),
            "LOAD": m.load_load[:periods].tolist(),
        },
        reserve_requirement_mw=m.reserve_req[:periods].tolist(),
        periods=periods,
    )
    cfd = CfdContract(
        strike_price=body.cfd_strike,
        quantity=body.cfd_quantity,
        reference_px=float(np.mean(m.lmp_load_history)),
    )
    rep = run_backtest(
        clearing_req=req,
        history_lmp=m.lmp_load_history,
        load_node=body.load_node,
        forecast_model=body.model,
        cfd=cfd,
    )
    return BacktestReportOut(
        periods=rep.periods,
        strategy_baseline=StrategyReportOut(**rep.strategy_baseline.model_dump()),
        strategy_forecast=StrategyReportOut(**rep.strategy_forecast.model_dump()),
        pnl_curve_baseline=rep.pnl_curve_baseline,
        pnl_curve_forecast=rep.pnl_curve_forecast,
        beats_baseline=rep.beats_baseline,
        summary_zh=rep.summary_zh,
        summary_en=rep.summary_en,
    )
