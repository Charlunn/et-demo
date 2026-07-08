"""应用配置 (SPEC §4.1).

所有业务门限/价差/时限/预算集中在此, 从 env 读取, 业务代码零裸数字.
SECRET_KEY fail-fast: 非 debug 模式下等于占位默认值或过短直接拒启动.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 占位默认值 — 非 debug 模式持有它即为配置错误 (SPEC §4.1).
_DEFAULT_SECRET = "dev-only-do-not-use-in-production-please-change-me-32chars-min"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "spark-pricing"
    debug: bool = True

    # ---- Database ----
    database_url: str = "sqlite+aiosqlite:///./spark.db"

    # ---- Security ----
    secret_key: str = _DEFAULT_SECRET
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"
    demo_user: str = "trader"
    demo_password: str = "trader-secret"
    demo_scopes: str = "backtest:run"

    # CORS allowlist (prod 默认空列表). 环境变量以 JSON 数组串传入.
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8501"])

    # ---- Domain / business defaults ----
    default_forecaster: Literal["persistence", "xgboost", "lstm"] = "persistence"
    risk_markup: float = 0.0
    reserve_requirement_mw: float = 20.0
    line_flow_limit_mw: float = 80.0
    retention_raw_days: int = 30

    # ---- Frontend / API ----
    backend_api_url: str = "http://localhost:8000"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v: object) -> object:
        # Accept a JSON array string from env ("[\"http://...\"]") or a list.
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"cors_origins is not valid JSON: {v!r}") from exc
            # comma-separated fallback
            return [part.strip() for part in v.split(",") if part.strip()]
        return v

    @model_validator(mode="after")
    def _validate_secret(self) -> Settings:
        # SPEC §4.1: 非 debug 下默认值/过短 -> 拒启动 (fail-fast).
        if not self.debug:
            if self.secret_key == _DEFAULT_SECRET:
                raise ValueError(
                    "SECRET_KEY 必须在生产环境(DEBUG=false)显式设置, 不可使用占位默认值"
                )
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY 在生产环境(DEBUG=false)必须 >=32 字符")
            if "*" in self.secret_key:
                raise ValueError("SECRET_KEY 不可包含 '*' 占位符")
        return self


# 单例: 进程内复用. 测试通过 monkeypatch 或直接构造新 Settings 覆盖.
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
