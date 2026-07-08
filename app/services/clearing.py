"""出清 service (SPEC §3.2): 调 domain/clearing_engine 解 LP, 组装响应."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.domain.clearing_engine import ClearingInput, ClearingResult, solve_clearing
from app.domain.units import Network, Unit


@dataclass(frozen=True)
class ClearingRequestDTO:
    units: list[Unit]
    network: Network
    load_per_node: dict[str, list[float]]
    reserve_requirement_mw: list[float]
    periods: int


def run_clearing(
    req: ClearingRequestDTO, *, line_flow_limit_mw: float | None = None
) -> ClearingResult:
    """跑日前出清. 可选覆盖线路潮流上限以复现阻塞."""
    network = req.network
    if line_flow_limit_mw is not None:
        network = Network(
            reference_node=network.reference_node,
            load_node=network.load_node,
            line_flow_limit_mw=line_flow_limit_mw,
        )
    inp = ClearingInput(
        units=req.units,
        network=network,
        load_per_node=req.load_per_node,
        reserve_requirement_mw=req.reserve_requirement_mw
        or [settings.reserve_requirement_mw] * req.periods,
        periods=req.periods,
    )
    return solve_clearing(inp)
