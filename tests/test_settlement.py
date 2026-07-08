"""结算三层手算对照测试 (SPEC §6)."""

from __future__ import annotations

import pytest

from app.domain.settlement import CfdContract, settle


def test_three_layer_handcalc_basic():
    """给定输入手算:
    S_da=100 MWh, S_act=110 MWh, LMP_da=300, LMP_rt=350.
    CfD: P_c=280, Q_c=50, LMP_ref=300.
    DA   = 100 * 300        = 30000
    DEV  = (110-100) * 350  = 3500
    CFD  = (280-300) * 50   = -1000
    TOTAL = 32500
    """
    bd = settle(
        s_da=100.0,
        s_act=110.0,
        lmp_da=300.0,
        lmp_rt=350.0,
        cfd=CfdContract(strike_price=280.0, quantity=50.0, reference_px=300.0),
    )
    assert pytest.approx(30000.0, abs=1e-6) == bd.da
    assert pytest.approx(3500.0, abs=1e-6) == bd.deviation
    assert pytest.approx(-1000.0, abs=1e-6) == bd.cfd
    assert pytest.approx(32500.0, abs=1e-6) == bd.total


def test_negative_deviation_overgeneration():
    """实际 < 日前计划(欠发) -> 偏差为负 (少收/倒付, 视方向). 手算:
    S_da=100, S_act=80, LMP_da=300, LMP_rt=500.
    DA  = 30000 ; DEV = (80-100)*500 = -10000 ; TOTAL=20000.
    """
    bd = settle(s_da=100.0, s_act=80.0, lmp_da=300.0, lmp_rt=500.0)
    assert pytest.approx(30000.0, abs=1e-6) == bd.da
    assert pytest.approx(-10000.0, abs=1e-6) == bd.deviation
    assert bd.cfd == 0.0
    assert pytest.approx(20000.0, abs=1e-6) == bd.total


def test_no_double_counting_when_actual_equals_plan():
    """实际==计划 -> 偏差 0, 仅日前结算 (避免双计价, SPEC §2 坑)."""
    bd = settle(s_da=100.0, s_act=100.0, lmp_da=300.0, lmp_rt=999.0)
    assert bd.deviation == 0.0
    assert pytest.approx(30000.0, abs=1e-6) == bd.total


def test_cfd_profitable_when_strike_above_ref():
    """中长期赚: 合约价高于现货参考价 -> 正差价."""
    bd = settle(
        s_da=0.0,
        s_act=0.0,
        lmp_da=0.0,
        lmp_rt=0.0,
        cfd=CfdContract(strike_price=400.0, quantity=20.0, reference_px=350.0),
    )
    assert pytest.approx(1000.0, abs=1e-6) == bd.cfd
    assert pytest.approx(1000.0, abs=1e-6) == bd.total


def test_settle_without_cfd_defaults_zero():
    bd = settle(s_da=10.0, s_act=12.0, lmp_da=100.0, lmp_rt=150.0)
    assert bd.cfd == 0.0
    assert pytest.approx(1000.0, abs=1e-6) == bd.da
    assert pytest.approx(300.0, abs=1e-6) == bd.deviation
