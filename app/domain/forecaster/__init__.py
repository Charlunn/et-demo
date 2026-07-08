"""价格预测 (SPEC §3.4): Forecaster ABC + Persistence 默认 + XGBoost 可选 + LSTM stub."""

from app.domain.forecaster.base import Forecaster
from app.domain.forecaster.factory import get_forecaster

__all__ = ["Forecaster", "get_forecaster"]
