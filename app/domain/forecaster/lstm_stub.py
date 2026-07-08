"""LSTM 预测 stub (SPEC §3.4).

绝不把 LSTM 标成真结果. __init__ log warn, forecast 返回 Persistence 结果. 注释明示
真 LSTM 需 GPU + 大量数据 + 训练管线, 超出 demo 1h 范围 (ADR 0002).
"""

from __future__ import annotations

import numpy as np

from app.domain.forecaster.base import Forecaster
from app.domain.forecaster.persistence import PersistenceForecaster
from app.core.logging import get_logger

log = get_logger(__name__)


class LSTMForecaster(Forecaster):
    name = "lstm"

    def __init__(self) -> None:
        # WARN: stub, returns persistence; real LSTM needs GPU/large data.
        log.warning("lstm_stub_loaded", detail="LSTM is a stub; returning persistence output")

    def forecast(self, history: np.ndarray, horizon: int) -> np.ndarray:
        return PersistenceForecaster().forecast(history, horizon)