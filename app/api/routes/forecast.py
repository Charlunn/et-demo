"""预测端点 (SPEC §5): POST /forecast 预测 LMP (可切模型名)."""

from __future__ import annotations

from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, Request, status

from app.core.ratelimit import limiter
from app.core.security import get_current_user
from app.schemas.backtest import ForecastOut, ForecastRequest
from app.services.forecast_service import run_forecast
from scripts.seed_demo import seed_market

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.post(
    "",
    response_model=ForecastOut,
    status_code=status.HTTP_200_OK,
    summary="预测节点 LMP (persistence|xgboost|lstm; 缺包回退 persistence)",
)
@limiter.limit("20/minute")
async def post_forecast(
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
    body: ForecastRequest,
) -> ForecastOut:
    m = seed_market(days=body.seed_days)
    hist = m.lmp_load_history if body.target_node == "LOAD" else m.lmp_ref_history
    out = run_forecast(np.asarray(hist), body.horizon, body.model_name)
    return ForecastOut(values=out.values, model_name=out.model_name)
