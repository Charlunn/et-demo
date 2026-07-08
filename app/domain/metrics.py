"""回测指标 (SPEC §3.5). 纯函数, 除零保护.

- 总收益 Net PnL
- 命中率 Hit Rate (预测方向正确的时段占比)
- 盈亏比 Profit Factor (盈利之和 / 亏损绝对值之和)
- 信息比率 per-trade Sharpe: mean(hourly PnL)/std * sqrt(8760)
- 出清价 MAPE / MAE
- 最大回撤 Max Drawdown
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class StrategyMetrics:
    net_pnl: float
    hit_rate: float
    profit_factor: float
    information_ratio: float
    clearing_mape: float
    clearing_mae: float
    max_drawdown: float


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if abs(b) > 1e-12 else default


def compute_metrics(
    *,
    pnl_series: np.ndarray,
    hit_flags: np.ndarray | None = None,
    forecast_prices: np.ndarray | None = None,
    actual_prices: np.ndarray | None = None,
    annualization: int = 8760,
) -> StrategyMetrics:
    """计算单策略指标. pnl_series 为逐时段累计盈亏增量 (每小时/时段)."""
    pnl = np.asarray(pnl_series, dtype=float).ravel()
    net_pnl = float(pnl.sum() if pnl.size else 0.0)

    # 命中率: 正盈亏时段占比 (或显式命中标).
    if hit_flags is not None:
        flags = np.asarray(hit_flags, dtype=bool).ravel()
        hit_rate = _safe_div(float(flags.sum()), float(flags.size), 0.0)
    else:
        if pnl.size:
            hits = float((pnl > 0).sum())
            nonzero = float((pnl != 0).sum()) or float(pnl.size)
            hit_rate = _safe_div(hits, nonzero, 0.0)
        else:
            hit_rate = 0.0

    # 盈亏比
    gains = float(pnl[pnl > 0].sum()) if pnl.size else 0.0
    losses = float(-pnl[pnl < 0].sum()) if pnl.size else 0.0
    profit_factor = _safe_div(gains, losses, float("inf") if gains > 0 else 0.0)

    # 信息比率 (per-trade Sharpe 年化)
    std = float(pnl.std()) if pnl.size > 1 else 0.0
    mean = float(pnl.mean()) if pnl.size else 0.0
    information_ratio = _safe_div(mean, std, 0.0) * float(np.sqrt(annualization))

    # 出清价 MAPE / MAE
    clearing_mape = 0.0
    clearing_mae = 0.0
    if forecast_prices is not None and actual_prices is not None:
        f = np.asarray(forecast_prices, dtype=float).ravel()
        a = np.asarray(actual_prices, dtype=float).ravel()
        n = min(f.size, a.size)
        if n > 0:
            ae = np.abs(f[:n] - a[:n])
            clearing_mae = float(ae.mean())
            denom = np.abs(a[:n])
            mape = np.where(denom > 1e-9, ae / np.maximum(denom, 1e-9), 0.0)
            clearing_mape = float(np.mean(mape) * 100.0)

    # 最大回撤 (基于营收累计)
    cum = np.cumsum(pnl) if pnl.size else np.array([0.0])
    running_max = np.maximum.accumulate(cum)
    drawdowns = running_max - cum
    max_drawdown = float(drawdowns.max() if drawdowns.size else 0.0)
    if not np.isfinite(max_drawdown):
        max_drawdown = 0.0

    if not np.isfinite(profit_factor):
        profit_factor = float("inf")
    return StrategyMetrics(
        net_pnl=net_pnl,
        hit_rate=hit_rate,
        profit_factor=profit_factor,
        information_ratio=information_ratio,
        clearing_mape=clearing_mape,
        clearing_mae=clearing_mae,
        max_drawdown=max_drawdown,
    )
