"""预测与回测 schema (SPEC §5)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    horizon: int = Field(96, ge=1, le=96, description="预测步数")
    model_name: str | None = Field(None, description="persistence|xgboost|lstm; 缺用 settings 默认")
    seed_days: int = Field(2, ge=1, le=30, description="合成历史天数 (用于滚动预测背景)")
    target_node: str = Field("LOAD", description="预测目标节点 LMP")

    model_config = {"json_schema_extra": {"example": {"horizon": 96, "model_name": "persistence"}}}


class ForecastOut(BaseModel):
    values: list[float]
    model_name: str
    honesty: str = "Persistence/XGBoost 真跑; LSTM 仅 stub"


class BacktestRequest(BaseModel):
    days: int = Field(1, ge=1, le=7, description="回测天数 (1天=96时段)")
    line_flow_limit_mw: float = Field(80.0, gt=0.0, le=2000.0)
    model: str | None = Field(None, description="预测模型名; None 用 settings 默认")
    load_node: str = Field("LOAD")
    cfd_strike: float = Field(300.0, ge=0.0, le=5000.0)
    cfd_quantity: float = Field(1000.0, ge=0.0, le=1_000_000.0)

    model_config = {"json_schema_extra": {"example": {"days": 1, "model": "persistence"}}}


class StrategyReportOut(BaseModel):
    name: str
    model_name: str
    metrics: dict[str, float]


class BacktestReportOut(BaseModel):
    periods: int
    strategy_baseline: StrategyReportOut
    strategy_forecast: StrategyReportOut
    pnl_curve_baseline: list[float]
    pnl_curve_forecast: list[float]
    beats_baseline: bool
    summary_zh: str
    summary_en: str
