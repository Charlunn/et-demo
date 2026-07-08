"""生成可复现的合成行情 (SPEC §2 scripts/seed_demo.py).

固定 seed: 负荷 + LMP 历史 + 机组参数. 生成 multi-period 负荷与结算用历史价, 供
回测与 CLI 复现. 不真爬虫/不接真实平台 (SPEC §4 out-of-scope), 但注释来源与 seed.

无 IO 副作用: 返回纯数据结构, 落盘与否由调用方决定 (CLI 可选写 demo-data/).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.domain.clearing_engine import ClearingInput
from app.domain.units import default_network, default_units

SEED = 20240101  # 固定 seed, 复现合成数据.

PERIODS_PER_DAY = 96  # 一天 96 个 15-min 时段.


@dataclass(frozen=True)
class SeededMarket:
    units: list  # type: ignore[type-arg]
    network: object
    load_ref: np.ndarray  # (T,) MW
    load_load: np.ndarray  # (T,) MW
    reserve_req: np.ndarray  # (T,) MW
    lmp_ref_history: np.ndarray  # (T,) 历史参考节点 LMP (出清产物 + 合成噪声)
    lmp_load_history: np.ndarray  # (T,) 历史负荷节点 LMP
    actual_energy_history: np.ndarray  # (T,) 实际发电量历史 (对偏差结算)


def seed_market(days: int = 2, line_flow_limit_mw: float = 80.0, seed: int = SEED) -> SeededMarket:
    """生成 days 天合成负荷/历史 LMP. T = days * 96."""
    rng = np.random.default_rng(seed)
    units = default_units()
    network = default_network(line_flow_limit_mw)
    T = days * PERIODS_PER_DAY

    # 负荷: 日内双峰 (早晚高峰) + 线性趋势 + 小噪声. 两节点负荷形状相似但 LOAD 更高.
    # 日内分量以 PERIODS_PER_DAY 为周期.
    phase = np.arange(T) % PERIODS_PER_DAY
    day_shape = 0.5 * (1 - np.cos(2 * np.pi * phase / PERIODS_PER_DAY))  # 0..1, 一峰
    base_ref = 90.0 + 30.0 * day_shape + rng.normal(0, 3, T)
    base_load = 140.0 + 40.0 * day_shape + rng.normal(0, 4, T)
    load_ref = np.maximum(base_ref, 0.0)
    load_load = np.maximum(base_load, 0.0)

    # 备用需求: 8% 负荷.
    reserve_req = np.maximum(0.08 * (load_ref + load_load), 5.0)
    # 合成历史 LMP: 以基荷边际成本上下浮动 + 拥塞加成
    lmp_ref_hist = 25.0 + 30.0 * day_shape + rng.normal(0, 5, T)
    lmp_load_hist = lmp_ref_hist + rng.normal(18.0, 6.0, T)
    lmp_ref_hist = np.maximum(lmp_ref_hist, 0.0)
    lmp_load_hist = np.maximum(lmp_load_hist, 0.0)
    # 实际发电历史 ≈ 计划 + ±5% 偏差噪声
    actual_energy_hist = (load_ref + load_load) * (1.0 + rng.normal(0, 0.05, T))

    return SeededMarket(
        units=units,
        network=network,
        load_ref=load_ref,
        load_load=load_load,
        reserve_req=reserve_req,
        lmp_ref_history=lmp_ref_hist,
        lmp_load_history=lmp_load_hist,
        actual_energy_history=actual_energy_hist,
    )


def to_clearing_input(market: SeededMarket, periods: int | None = None) -> ClearingInput:
    """把 seed 数据装成出清输入 (可选截取前 periods 段)."""
    T = periods or market.load_ref.size
    return ClearingInput(
        units=market.units,
        network=market.network,
        load_per_node={
            "REF": market.load_ref[:T].tolist(),
            "LOAD": market.load_load[:T].tolist(),
        },
        reserve_requirement_mw=market.reserve_req[:T].tolist(),
        periods=T,
    )
