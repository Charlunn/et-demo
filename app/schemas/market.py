"""行情与实时流 schema (SPEC §5)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LmpPoint(BaseModel):
    ts: datetime
    node: str
    value: float


class LoadPoint(BaseModel):
    ts: datetime
    node: str
    value: float


class MarketView(BaseModel):
    lmp: list[LmpPoint]
    load: list[LoadPoint]
    blocked_periods: list[int] = Field(default_factory=list, description="出现阻塞的时段序号")


class PriceTick(BaseModel):
    ts: datetime
    node_id: str
    series_type: str
    value: float
    quality_flag: str = "OK"
