"""出清 schema (SPEC §5)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClearingRequest(BaseModel):
    periods: int = Field(96, ge=1, le=96, description="出清时段数 (15-min 步, 上限一日96)")
    line_flow_limit_mw: float = Field(80.0, gt=0.0, le=2000.0, description="线路潮流上限, 制造阻塞")
    load_ref: list[float] = Field(
        ..., min_length=1, description="参考节点逐时段负荷 MW (长度=periods)"
    )
    load_load: list[float] = Field(..., min_length=1, description="负荷节点逐时段负荷 MW")
    reserve_requirement_mw: list[float] | None = Field(
        None, description="逐时段备用需求; 缺则用 settings 默认"
    )
    days: int = Field(1, ge=1, le=7, description="若留空, 用 seed 合成 days 天数据")
    use_seed: bool = Field(
        True, description="用可复现 seed 数据填充负荷 (否则用 load_ref/load_load)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "periods": 96,
                "line_flow_limit_mw": 80.0,
                "days": 1,
                "use_seed": True,
                "load_ref": [100.0],
                "load_load": [150.0],
            }
        }
    }


class PeriodResultOut(BaseModel):
    period: int
    p: dict[str, float]
    r: dict[str, float]
    lmp: dict[str, float]
    lmp_components: dict[str, dict[str, float]]
    line_flow_mw: float
    blocked: bool


class ClearingResultOut(BaseModel):
    status: str
    total_cost: float
    periods: list[PeriodResultOut]
