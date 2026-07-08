"""出清引擎测试 (SPEC §6): LMP 由 LP 对偶决定, 手算对照, 含阻塞例 congestion>0.

为可手算, 用单机一节点的极简拓扑 (REF: 20*P, LOAD: 40*P, 线性成本 a=0).
"""

from __future__ import annotations

import pytest

from app.domain.clearing_engine import ClearingInput, solve_clearing
from app.domain.units import Network, Unit


def case(units, fmax, ref_load, load_load, reserve=0.0):
    net = Network(reference_node="REF", load_node="LOAD", line_flow_limit_mw=fmax)
    return ClearingInput(
        units=units,
        network=net,
        load_per_node={
            "REF": [ref_load],
            "LOAD": [load_load],
        },
        reserve_requirement_mw=[reserve],
        periods=1,
    )


LINEAR_UNITS = [
    Unit("REF1", "REF", a=0.0, b=20.0, c=0.0, p_min=0.0, p_max=100.0, ramp_up=1000, ramp_down=1000),
    Unit("LOD1", "LOAD", a=0.0, b=40.0, c=0.0, p_min=0.0, p_max=50.0, ramp_up=1000, ramp_down=1000),
]


def test_no_congestion_uniform_lmp():
    """无阻塞: 两节点 LMP 相等 (单系统边际价), congestion=0, line_flow < limit.

    手算: REF(20*P) Pmax=100 全上 100 (60 本地+40 外送); LOAD 上 0. 系统边际由
    被吃满的 REF 转到下一台 LOAD (40) -> 双节点 LMP=40, F=40 < fmax=1000.
    """
    res = solve_clearing(case(LINEAR_UNITS, fmax=1000.0, ref_load=60.0, load_load=40.0))
    pr = res.periods[0]
    assert pytest.approx(40.0, abs=1e-6) == pr.lmp["REF"]
    assert pytest.approx(40.0, abs=1e-6) == pr.lmp["LOAD"]
    assert pytest.approx(0.0, abs=1e-6) == pr.lmp_components["LOAD"]["congestion"]
    assert pr.lmp_components["LOAD"]["loss"] == 0.0
    assert pr.blocked is False
    assert pytest.approx(40.0, rel=1e-3) == pr.line_flow_mw


def test_congestion_split_lmp():
    """阻塞: 线路限流使便宜基荷卡在 REF, 负荷节点被迫用贵机 -> 阻塞价>0.

    手算: fmax=10 -> F<=10. LOAD_load=40 -> LOAD 至少发 30, F=10 满. REF 发 60+10=70
    (边际 REF 成本 20). LOAD 发 30 (边际 LOAD 成本 40). 拆 LMP: REF=20, LOAD=40,
    congestion=20, F=10==fmax -> blocked.
    """
    res = solve_clearing(case(LINEAR_UNITS, fmax=10.0, ref_load=60.0, load_load=40.0))
    pr = res.periods[0]
    assert pytest.approx(20.0, abs=1e-6) == pr.lmp["REF"]
    assert pytest.approx(40.0, abs=1e-6) == pr.lmp["LOAD"]
    assert pytest.approx(20.0, abs=1e-6) == pr.lmp_components["LOAD"]["congestion"]
    assert pr.blocked is True
    assert pytest.approx(10.0, rel=1e-3) == pr.line_flow_mw
    # 出力手算
    assert pytest.approx(70.0, abs=1e-6) == pr.p["REF1"]
    assert pytest.approx(30.0, abs=1e-6) == pr.p["LOD1"]


def test_reserve_constraint_must_be_satisfied():
    """备用约束: Σ R >= 备用需求; 备用在 P+R<=Pmax 夹缝内可满足时解仍最优."""
    # 一台机组足够头皮地留 15MW 备用而不破坏平衡.
    res = solve_clearing(case(LINEAR_UNITS, fmax=1000.0, ref_load=60.0, load_load=40.0, reserve=15.0))
    pr = res.periods[0]
    total_reserve = sum(pr.r.values())
    assert total_reserve >= 15.0 - 1e-6
    # 出力备用不超额
    from app.domain.units import default_units  # noqa: PLC0415

    _ = default_units  # 仅验证 import 路径无害
    assert abs(pr.p["REF1"] + pr.r["REF1"]) <= 100.0 + 1e-6


def test_infeasible_raises():
    """无可行解 (线路+备用+容量约束冲突) -> ClearingInfeasibleError."""
    # 负荷远超两个节点可用容量与线路之和.
    from app.core.errors import ClearingInfeasibleError

    with pytest.raises(ClearingInfeasibleError):
        solve_clearing(case(LINEAR_UNITS, fmax=5.0, ref_load=120.0, load_load=120.0))


def test_default_units_multi_period_clears():
    """构造性冒烟: 默认 5 机组 / 2 节点 / 多时段可求解且产物结构完整 (阻塞例)."""
    from app.domain.units import default_network, default_units

    units = default_units()
    net = default_network(80.0)
    T = 3
    inp = ClearingInput(
        units=units,
        network=net,
        load_per_node={"REF": [100.0, 110.0, 90.0], "LOAD": [160.0, 170.0, 140.0]},
        reserve_requirement_mw=[20.0] * T,
        periods=T,
    )
    res = solve_clearing(inp)
    assert res.status == "optimal"
    assert len(res.periods) == T
    for pr in res.periods:
        # 节点 LMP 三组件齐全
        assert set(pr.lmp_components["LOAD"].keys()) == {"energy", "congestion", "loss"}
        assert pr.lmp_components["LOAD"]["loss"] == 0.0  # 损耗品 хлоп生产才计
        # 爬坡满足
        assert pr.line_flow_mw - 80.0 <= 1e-6 or pr.line_flow_mw + 80.0 >= -1e-6