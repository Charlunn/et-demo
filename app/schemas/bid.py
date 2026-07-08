"""报价 schema (SPEC §5). 不让前端手填 JSON: /bids 仅收 unit_id+strategy+risk_markup."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UnitOut(BaseModel):
    unit_id: str
    node_id: str
    a: float = Field(..., description="二次成本系数 (元/MWh^2)")
    b: float = Field(..., description="一次成本系数 (元/MWh)")
    c: float = Field(..., description="常数项 (元/h)")
    p_min: float
    p_max: float
    ramp_up: float
    ramp_down: float
    is_must_run: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "unit_id": "G1",
                "node_id": "REF",
                "a": 0.02,
                "b": 20.0,
                "c": 0.0,
                "p_min": 0.0,
                "p_max": 120.0,
                "ramp_up": 60.0,
                "ramp_down": 60.0,
                "is_must_run": False,
            }
        }
    }


class BidSubmit(BaseModel):
    unit_id: str = Field(..., min_length=1, max_length=32, examples=["G1"])
    strategy: str = Field(
        "marginal", examples=["marginal"], description="marginal 或 marginal_plus_forecast"
    )
    risk_markup: float = Field(0.0, ge=0.0, le=500.0, description="风险加成 (元/MWh), 非负")
    forecast_lmp: float | None = Field(
        None, ge=0.0, le=2000.0, description="策略2用的预测加成参考 LMP"
    )
    periods: int = Field(96, ge=1, le=96, description="生成多少时段报价 (单机单时段填1)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "unit_id": "G1",
                "strategy": "marginal",
                "risk_markup": 5.0,
                "periods": 96,
            }
        }
    }


class BidSegmentOut(BaseModel):
    price: float
    mw: float


class BidCurveOut(BaseModel):
    unit_id: str
    period: int
    strategy: str
    segments: list[BidSegmentOut]
    segment_count: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "unit_id": "G1",
                "period": 0,
                "strategy": "marginal",
                "segments": [{"price": 20.0, "mw": 12.0}],
                "segment_count": 10,
            }
        }
    }
