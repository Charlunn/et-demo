"""机组成本曲线与运行参数 (SPEC §3.1).

二次成本 C(P) = a*P^2 + b*P + c; 边际成本 dC/dP = 2aP + b.
分段报价由 services/generation_bids 基于边际成本切 ≤10 段.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Unit:
    """一台发电机组."""

    unit_id: str
    node_id: str  # 所在节点 (参考节点或负荷节点)
    a: float  # 二次项 (元/MWh^2), 非负
    b: float  # 一次项 (元/MWh)
    c: float  # 常数项 (元/h), 可再生/空载
    p_min: float  # 最小技术出力 (MW)
    p_max: float  # 最大技术出力 (MW)
    ramp_up: float  # 爬坡上限 (MW/时段)
    ramp_down: float  # 下行爬坡上限 (MW/时段), 取正数
    is_must_run: bool = False  # 可再生必发 (不参与可停机)

    @property
    def name(self) -> str:
        return self.unit_id

    def cost(self, p: float) -> float:
        """总成本 C(P)=aP^2+bP+c (元/h)."""
        return self.a * p * p + self.b * p + self.c

    def marginal_cost(self, p: float) -> float:
        """边际成本 dC/dP = 2aP + b (元/MWh)."""
        return 2.0 * self.a * p + self.b

    def reserve_capacity(self) -> float:
        """可提供旋转备用的余量: P_max 向上的可调度空间 (假设 P 当前 >= P_min)."""
        # 备用容量上限 = P_max - P (在出力 P 之上), 此处给出最大可能 = P_max - P_min.
        return self.p_max - self.p_min


@dataclass(frozen=True)
class Network:
    """2 节点网络 (SPEC §3.2). 节点间单条线路, 潮流上限制造阻塞."""

    reference_node: str
    load_node: str
    line_flow_limit_mw: float  # |F| <= F_max, 制造阻塞

    @property
    def nodes(self) -> list[str]:
        return [self.reference_node, self.load_node]


# ---- demo 算例的默认机组集 (固定位, 便于手算对照与 seed 复现) ----
# 5 台机组: 3 台在参考节点(ref), 2 台在负荷节点(load). 拓扑: ref --|F_max=80|--> load.
# 成本为二次函数; 页岩式便宜基荷在 ref, 较贵峰荷在 load; 这样受限线路会把 ref 的便宜电
# 卡住, 使负荷节点 LMP 高于参考节点 -> 产生阻塞价.
def default_units() -> list[Unit]:
    return [
        Unit(
            "G1", "REF", a=0.02, b=20.0, c=0.0, p_min=0.0, p_max=120.0, ramp_up=60.0, ramp_down=60.0
        ),
        Unit(
            "G2", "REF", a=0.03, b=25.0, c=0.0, p_min=0.0, p_max=100.0, ramp_up=50.0, ramp_down=50.0
        ),
        Unit(
            "G3", "REF", a=0.05, b=30.0, c=0.0, p_min=0.0, p_max=80.0, ramp_up=40.0, ramp_down=40.0
        ),
        Unit(
            "G4", "LOAD", a=0.01, b=40.0, c=0.0, p_min=0.0, p_max=60.0, ramp_up=40.0, ramp_down=40.0
        ),
        Unit(
            "G5", "LOAD", a=0.02, b=45.0, c=0.0, p_min=0.0, p_max=50.0, ramp_up=30.0, ramp_down=30.0
        ),
    ]


def default_network(line_flow_limit_mw: float = 80.0) -> Network:
    return Network(reference_node="REF", load_node="LOAD", line_flow_limit_mw=line_flow_limit_mw)
