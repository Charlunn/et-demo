"""回测测试 (SPEC §6): run_backtest 出报告, 字段非空, 策略2胜基线, 除零保护."""

import numpy as np
import pytest

from app.domain.units import default_network, default_units
from app.services.backtest import run_backtest
from app.services.clearing import ClearingRequestDTO
from scripts.seed_demo import seed_market


@pytest.fixture
def seeded_req():
    m = seed_market(days=1, line_flow_limit_mw=80.0)
    units = default_units()
    net = default_network(80.0)
    from app.domain.clearing_engine import ClearingInput

    ci = ClearingInput(
        units=units,
        network=net,
        load_per_node={"REF": m.load_ref[:96].tolist(), "LOAD": m.load_load[:96].tolist()},
        reserve_requirement_mw=m.reserve_req[:96].tolist(),
        periods=96,
    )
    req = ClearingRequestDTO(
        units=units,
        network=net,
        load_per_node=ci.load_per_node,
        reserve_requirement_mw=ci.reserve_requirement_mw,
        periods=96,
    )
    return req, m


def test_backtest_report_fields_nonempty(seeded_req):
    req, m = seeded_req
    rep = run_backtest(clearing_req=req, history_lmp=m.lmp_load_history[:96], load_node="LOAD")
    assert rep.periods == 96
    assert len(rep.pnl_curve_baseline) == 96
    assert len(rep.pnl_curve_forecast) == 96
    assert rep.summary_zh  # 非空中文小结
    assert rep.summary_en
    assert set(rep.strategy_baseline.metrics) >= {
        "net_pnl",
        "hit_rate",
        "profit_factor",
        "information_ratio",
        "clearing_mape",
        "max_drawdown",
    }


def test_strategy2_beats_baseline(seeded_req):
    req, m = seeded_req
    rep = run_backtest(clearing_req=req, history_lmp=m.lmp_load_history[:96], load_node="LOAD")
    assert rep.beats_baseline is True
    assert (
        rep.strategy_forecast.metrics["net_pnl"] >= rep.strategy_baseline.metrics["net_pnl"] - 1e-9
    )


def test_pnl_finite_and_bounded(seeded_req):
    req, m = seeded_req
    rep = run_backtest(clearing_req=req, history_lmp=m.lmp_load_history[:96], load_node="LOAD")
    for v in rep.pnl_curve_baseline:
        assert np.isfinite(v)
    for v in rep.pnl_curve_forecast:
        assert np.isfinite(v)


def test_metrics_divzero_safe():
    # 零 PnL 序列 -> 指标不 NaN/inf (除零保护).
    from app.domain.metrics import compute_metrics

    m = compute_metrics(pnl_series=np.zeros(5))
    assert np.isfinite(m.hit_rate)
    assert np.isfinite(m.information_ratio)
    assert m.max_drawdown == 0.0
