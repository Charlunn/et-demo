"""XGBoost 预测器 (可选依赖, SPEC §3.4).

import 失败时 get_forecaster 工厂回退 Persistence 并 log warn. 这里模型用滞后特征 +
日内相位做一次轻量梯度提升回归; 仅作"真 ML"演示, 不追求精度 (1h 内不调超参).
"""

from __future__ import annotations

import numpy as np

from app.domain.forecaster.base import Forecaster
from app.domain.forecaster.persistence import PERIODS_PER_DAY, PersistenceForecaster


class XGBoostForecaster(Forecaster):
    name = "xgboost"

    def forecast(self, history: np.ndarray, horizon: int) -> np.ndarray:
        try:
            from xgboost import XGBRegressor  # type: ignore[import-not-found]
        except ImportError:  # pragma: no cover - 工厂层早应回退, 此为防御兜底
            return PersistenceForecaster().forecast(history, horizon)

        if history.size == 0:
            return np.zeros(horizon, dtype=float)
        # 构造监督样本: 滞后窗口 + 日内相位. 用最近 window 步训练.
        window = PERIODS_PER_DAY
        X: list[list[float]] = []
        y: list[float] = []
        for i in range(window, history.size):
            X.append([*history[i - window : i], float(i % PERIODS_PER_DAY)])
            y.append(float(history[i]))
        if len(X) < 5:
            # 训练样本不足 -> 回退持久化, 不编造结果.
            return PersistenceForecaster().forecast(history, horizon)
        xa = np.asarray(X, dtype=float)
        ya = np.asarray(y, dtype=float)
        model = XGBRegressor(n_estimators=80, max_depth=3, learning_rate=0.1, verbosity=0, n_jobs=1)
        model.fit(xa, ya)
        # 自回归滚动预测 horizon 步.
        tail = list(history[-window:])
        out = np.empty(horizon, dtype=float)
        for k in range(horizon):
            feat = np.asarray(
                [*tail[-window:], float((history.size + k) % PERIODS_PER_DAY)], dtype=float
            ).reshape(1, -1)
            pred = float(model.predict(feat)[0])
            out[k] = max(pred, 0.0)
            tail.append(pred)
        return out
