"""分段报价测试 (SPEC §6): 段数≤10, 价格随边际成本单调, ≥0."""

from __future__ import annotations

import pytest

from app.domain.units import Unit
from app.services.bidding import build_bid_curve

U = Unit("G1", "REF", a=0.02, b=20.0, c=0.0, p_min=0.0, p_max=120.0, ramp_up=60, ramp_down=60)


def test_segment_count_leq_10():
    curve = build_bid_curve(U, strategy="marginal", risk_markup=0.0)
    assert curve.segment_count == 10


def test_prices_monotone_nonneg_with_risk_markup():
    curve = build_bid_curve(U, strategy="marginal", risk_markup=5.0)
    prices = [s.price for s in curve.segments]
    assert all(p >= 0.0 for p in prices)
    # 边际成本 2aP+b 单调增 (a>0), 加成应保持单调不减.
    for i in range(1, len(prices)):
        assert prices[i] >= prices[i - 1] - 1e-9


def test_forecast_strategy_carries_premium():
    curve_base = build_bid_curve(U, strategy="marginal_plus_forecast", forecast_lmp=500.0)
    curve_marg = build_bid_curve(U, strategy="marginal")
    # 当预测价远高于边际成本, 报价应高于纯边际报价.
    assert any(
        s_f.price > s_m.price
        for s_f, s_m in zip(curve_base.segments, curve_marg.segments, strict=True)
    )


def test_segment_mw_sums_to_capacity_span():
    curve = build_bid_curve(U)
    total_mw = sum(s.mw for s in curve.segments)
    assert pytest.approx(total_mw, rel=1e-9) == (U.p_max - U.p_min)