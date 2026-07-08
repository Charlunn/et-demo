"""结构化日志 + request_id 中间件 (SPEC §4.4).

prod: structlog JSON; dev: pretty console. 业务代码无 print().
LoggingMiddleware 注入 request_id 并记 method/path/status/duration_ms.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings


def configure_logging() -> None:
    """配置 structlog (进程内幂等)."""
    level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(level=level)
    # 抑制第三方库在 DEBUG 下的海量调试噪声 (业务仍可 debug 级记录).
    for noisy in ("aiosqlite", "httpx", "httpcore", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    if settings.debug:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.dict_tracebacks)
        processors.append(structlog.processors.JSONRenderer())
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        # stdlib LoggerFactory: 让 structlog 事件经标准 logging 路由, 以便 caplog/全局级别控制.
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]


def new_request_id() -> str:
    return uuid.uuid4().hex


def get_request_id(request: Request) -> str | None:
    """从请求上下文/响应头取 request_id, 用于 ProblemDetail 填充."""
    # LoggingMiddleware 已把 request_id 绑入 contextvar; 但 exception handler 在
    # dispatch 的之后?handler 由 FastAPI 异常机制在上层调用, contextvar 可能未绑,
    # 故优先从已写入的响应头/入参头回退.
    ctx = structlog.contextvars.get_contextvars()
    rid = ctx.get("request_id")
    if rid:
        return rid  # type: ignore[no-any-return]
    return request.headers.get("X-Request-ID")


class LoggingMiddleware(BaseHTTPMiddleware):
    """注入 request_id 并记录每次请求的 method/path/status/duration_ms.

    request_id 通过 response header `X-Request-ID` 回传, 供前后端联调, 并作为
    ProblemDetail 的 instance/request_id 字段.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or new_request_id()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        log = get_logger("http")
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000.0
            log.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000.0
            log.exception(
                "request_error",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()
