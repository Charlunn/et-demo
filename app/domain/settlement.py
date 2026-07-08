"""双结算三层 (SPEC §3.3). 纯函数, 易做手算对照.

日前结算      DA    = S_da * LMP_da
实时偏差结算  DEV   = (S_act - S_da) * LMP_rt   (仅偏差电量按实时价, 避免双重计价)
中长期差价    CFD   = (P_c - LMP_ref) * Q_c      (金融差价合约, 物理交付解耦)
三层收益(发电侧) TOTAL = DA + DEV + CFD
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CfdContract:
    """差价合约 (SPEC §3.3: 财金融合约, 物理交付解耦)."""

    strike_price: float  # 合约价 P_c (元/MWh)
    quantity: float  # 合约量 Q_c (MWh)
    reference_px: float  # 省级现货参考价 LMP_ref (元/MWh)


@dataclass(frozen=True)
class SettlementBreakdown:
    """三层结算明细 (纯值, 用于对照测试与前端呈现)."""

    da: float  # 日前结算金额 (元)
    deviation: float  # 实时偏差结算金额 (元)
    cfd: float  # 中长期差价金额 (元)
    total: float  # 三层收益合计 (元)

    def as_dict(self) -> dict[str, float]:
        return {"da": self.da, "deviation": self.deviation, "cfd": self.cfd, "total": self.total}


def settle(
    *,
    s_da: float,
    s_act: float,
    lmp_da: float,
    lmp_rt: float,
    cfd: CfdContract | None = None,
) -> SettlementBreakdown:
    """计算三层结算. 单位 MW/MWh 转为金额元.

    所有电量以 MWh 计 (15-min 时段 * 功率). 实时偏差结算只对 (实际 - 日前计划) 计实时价,
    日前计划电量照付, 避免双结算重复计价 (SPEC §2 域事实).
    """
    da = s_da * lmp_da
    deviation = (s_act - s_da) * lmp_rt
    cfd_amt = (cfd.strike_price - cfd.reference_px) * cfd.quantity if cfd else 0.0
    total = da + deviation + cfd_amt
    return SettlementBreakdown(da=da, deviation=deviation, cfd=cfd_amt, total=total)