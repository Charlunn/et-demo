"""报价生成 (SPEC §3.1). 纯函数.

给定机组 + 策略 -> 分段报价曲线 (≤10 段), 每段 (price, mw).
策略 1 (基线) "报边际成本": 每段价 = 边际成本 + risk_markup.
策略 2 "边际成本 + 预测加成": 每段价 = 边际成本 + risk_markup + forecast_premium[h],
  其中 forecast_premium 由预测 LMP - 该机组边际成本基准决定 (出清时才用, 生成报价时仅调).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.units import Unit

MAX_SEGMENTS = 10  # SPEC §3.1: 分段 ≤10.


@dataclass(frozen=True)
class BidSegment:
    price: float  # 元/MWh
    mw: float  # 该段容量 MW (递增量)


@dataclass(frozen=True)
class BidCurve:
    unit_id: str
    period: int
    strategy: str
    segments: list[BidSegment]

    @property
    def segment_count(self) -> int:
        return len(self.segments)


def build_bid_curve(
    unit: Unit,
    *,
    strategy: str = "marginal",
    risk_markup: float = 0.0,
    forecast_lmp: float | None = None,
    period: int = 0,
) -> BidCurve:
    """生成单机组单时段分段报价.

    - marginal: 每段价 = 边际成本(段中点) + risk_markup.
    - marginal_plus_forecast: 在 marginal 基础加上 (forecast_lmp - 段中点边际成本) 的
      缓和加成 alpha, 让报价带一点预测风格 (策略2, SPEC §3.1).
    """
    strategy = (strategy or "marginal").lower()
    span = unit.p_max - unit.p_min
    n = MAX_SEGMENTS
    seg_mw = span / n
    segments: list[BidSegment] = []
    for i in range(n):
        p_lo = unit.p_min + i * seg_mw
        mid = p_lo + seg_mw / 2.0
        mc = unit.marginal_cost(mid)
        price = mc + risk_markup
        if strategy.startswith("marginal_plus_forecast") and forecast_lmp is not None:
            # 加成 = 缓和的(forecast 高于边际的部分); alpha 控制激进程度.
            alpha = 0.5
            premium = alpha * max(forecast_lmp - mc, 0.0)
            price = mc + risk_markup + premium
        segments.append(BidSegment(price=max(price, 0.0), mw=seg_mw))
    return BidCurve(unit_id=unit.unit_id, period=period, strategy=strategy, segments=segments)