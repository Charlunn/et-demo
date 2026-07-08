"""预测 service (SPEC §3.4): 选 Forecaster 并跑预测."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.domain.forecaster import get_forecaster


@dataclass(frozen=True)
class ForecastResult:
    values: list[float]
    model_name: str


def run_forecast(
    history: np.ndarray, horizon: int, model_name: str | None = None
) -> ForecastResult:
    f = get_forecaster(model_name)
    vals = np.asarray(f.forecast(history, horizon), dtype=float).tolist()
    return ForecastResult(values=vals, model_name=f.name)
