"""Persistence 预测器 (SPEC §3.4).

零依赖, 实跑. price_{t+1} = price_t + 日周期项 (无穷小正则), 即: 最近一个完整日
周期的同相位价 + 线性漂移修正. 对平稳日内电价足够鲁棒, 也是 XGBoost/LSTM 的合理基准.
"""

from __future__ import annotations

import numpy as np

from app.domain.forecaster.base import Forecaster

# 一天 96 个 15-min 时段 (SPEC §2 硬事实集).
PERIODS_PER_DAY = 96


class PersistenceForecaster(Forecaster):
    name = "persistence"

    def forecast(self, history: np.ndarray, horizon: int) -> np.ndarray:
        if history.size == 0:
            # 无历史 -> 用 0 填充 (业务兜底, route/校验层应先拦空输入).
            return np.zeros(horizon, dtype=float)
        if horizon <= 0:
            return np.array([], dtype=float)
        out = np.empty(horizon, dtype=float)
        last = float(history[-1])
        if history.size >= PERIODS_PER_DAY:
            # 取昨日同相位序列作骨架, 修正近期漂移 (last - 昨日此刻).
            yesterday = history[-PERIODS_PER_DAY:]
            drift = last - float(yesterday[-1])
            for i in range(horizon):
                out[i] = float(yesterday[i % PERIODS_PER_DAY]) + drift
        else:
            # 历史不足一天 -> 持续最近价.
            out[:] = last
        # 非负价格 (电价非负, 偶发负 spot 除外; demo 视非负).
        return np.maximum(out, 0.0)