"""结算 schema (SPEC §5)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CfdInput(BaseModel):
    strike_price: float = Field(..., ge=0.0, le=5000.0, description="合约价 (元/MWh)")
    quantity: float = Field(..., ge=0.0, le=1_000_000.0, description="合约量 (MWh)")
    reference_px: float = Field(..., ge=0.0, le=5000.0, description="省级现货参考价 (元/MWh)")


class SettlementRequest(BaseModel):
    s_da: float = Field(..., ge=0.0, le=1_000_000.0, description="日前计划电量 (MWh)")
    s_act: float = Field(..., ge=0.0, le=1_000_000.0, description="实际电量 (MWh)")
    lmp_da: float = Field(..., ge=0.0, le=5000.0, description="日前 LMP (元/MWh)")
    lmp_rt: float = Field(..., ge=0.0, le=5000.0, description="实时 LMP (元/MWh)")
    cfd: CfdInput | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "s_da": 100.0,
                "s_act": 110.0,
                "lmp_da": 300.0,
                "lmp_rt": 350.0,
                "cfd": {"strike_price": 280.0, "quantity": 50.0, "reference_px": 300.0},
            }
        }
    }


class SettlementBreakdownOut(BaseModel):
    da: float
    deviation: float
    cfd: float
    total: float
    manual_check_note: str = (
        "与手算口径一致: DA=S_da*LMP_da; DEV=(S_act-S_da)*LMP_rt; CFD=(P_c-LMP_ref)*Q_c"
    )
