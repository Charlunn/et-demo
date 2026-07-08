"""领域异常基类 + 状态映射 (SPEC §4.3).

领域错误与 HTTP 解耦: 这里只定义异常与建议状态码;
把异常映射成 RFC7807 ProblemDetail 的 handler 在 main.py 装配 (依赖 FastAPI).
service 层抛本模块异常, 不导 FastAPI 类型.
"""

from __future__ import annotations


class DomainError(Exception):
    """领域异常基类. 携 status (建议 HTTP 状态码) 与 detail."""

    status: int = 400
    title: str = "Domain error"

    def __init__(self, detail: str, *, title: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if title is not None:
            self.title = title


class NotFoundError(DomainError):
    status = 404
    title = "Not found"


class BusinessValidationError(DomainError):
    """业务层校验失败 (区别于 Pydantic 422 的请求体校验)."""

    status = 422
    title = "Business validation error"


class ClearingInfeasibleError(DomainError):
    """LP 出清无可行解 (约束冲突 / 备用不可满足等)."""

    status = 422
    title = "Clearing infeasible"


class UnauthorizedError(DomainError):
    status = 401
    title = "Unauthorized"


class ForbiddenError(DomainError):
    status = 403
    title = "Forbidden"