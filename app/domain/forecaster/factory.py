"""Forecaster 工厂 (SPEC §3.4): 按名称选预测器, 缺依赖优雅回退 Persistence.

用法: get_forecaster("xgboost") -> 若 xgboost 未装则回退 persistence + warn.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.domain.forecaster.base import Forecaster
from app.domain.forecaster.lstm_stub import LSTMForecaster
from app.domain.forecaster.persistence import PersistenceForecaster
from app.domain.forecaster.xgboost_impl import XGBoostForecaster

log = get_logger(__name__)

_registry = {
    "persistence": PersistenceForecaster,
    "xgboost": XGBoostForecaster,
    "lstm": LSTMForecaster,
}


def get_forecaster(model_name: str | None = None) -> Forecaster:
    name = model_name or settings.default_forecaster
    name = name.lower()
    if name == "xgboost":
        try:
            import xgboost  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            log.warning(
                "forecaster_fallback",
                requested="xgboost",
                reason="xgboost not installed -> persistence",
            )
            return PersistenceForecaster()
        return XGBoostForecaster()
    if name == "lstm":
        return LSTMForecaster()
    if name == "persistence":
        return PersistenceForecaster()
    log.warning("forecaster_fallback", requested=name, reason="unknown model -> persistence")
    return PersistenceForecaster()


__all__ = ["get_forecaster", "Forecaster"]
