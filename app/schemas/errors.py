"""RFC7807 ProblemDetail (SPEC §4.3).

{type, title, status, detail, instance, request_id} 全局统一信封.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProblemDetail(BaseModel):
    type: str = Field(
        default="about:blank",
        description="问题类型 URI; 无具体类型时为 about:blank",
    )
    title: str = Field(..., description="简短可读问题标题")
    status: int = Field(..., description="HTTP 状态码 (与响应一致)")
    detail: str = Field(..., description="对问题的具体说明")
    instance: str | None = Field(default=None, description="问题发生处的路径/标识")
    request_id: str | None = Field(
        default=None,
        description="请求追踪 ID, 与响应头 X-Request-ID 一致",
    )

    model_config = {"json_schema_extra": {"example": {
        "type": "about:blank",
        "title": "Not found",
        "status": 404,
        "detail": "未找到机组",
        "instance": "/units/99",
        "request_id": "a1b2c3",
    }}}