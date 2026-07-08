"""FastAPI 实例装配 (SPEC §2).

装配: OpenAPI 元信息 / CORS allowlist / LoggingMiddleware (request_id) /
全局 ProblemDetail exception handlers / /token 颁发端点 / 路由挂载 /
startup-shutdown 日志. 路由按 P1 阶段陆续挂载.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import backtest, bids, clearing, forecast, health, market, settlement, stream
from app.core.config import settings
from app.core.errors import DomainError
from app.core.logging import LoggingMiddleware, configure_logging, get_logger, get_request_id
from app.core.security import authenticate_and_issue
from app.db.session import dispose_engine
from app.schemas.errors import ProblemDetail

log = get_logger(__name__)


def _problem(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    type_: str = "about:blank",
) -> JSONResponse:
    rid = get_request_id(request)
    body = ProblemDetail(
        type=type_,
        title=title,
        status=status_code,
        detail=detail,
        instance=str(request.url.path),
        request_id=rid,
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def create_app() -> FastAPI:
    configure_logging()

    @asynccontextmanager
    async def _lifespan(app: FastAPI):  # noqa: ARG001
        log.info("app_start", app=settings.app_name, debug=settings.debug)
        yield
        await dispose_engine()
        log.info("app_stop", app=settings.app_name)

    app = FastAPI(
        title="spark-pricing",
        version="0.1.0",
        description=(
            "电力现货交易端到端 demo: 负荷预测 → 分段报价 → 联合出清(LP,取对偶当 LMP) → "
            "双结算三层 → 回测复盘. 后端 + 数据 + Streamlit 产品工作台, 整体可搬进对方系统."
        ),
        debug=settings.debug,
        lifespan=_lifespan,
    )

    # ---- CORS allowlist (SPEC §4.5). prod 空列表; 通配被拒. ----
    if "*" in settings.cors_origins:
        raise RuntimeError("CORS allowlist 不可在 prod 配置通配 '*' (SPEC §4.5)")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware)

    # ---- slowapi 限流 (SPEC §4.5): 各写端点 @limiter.limit; 全局 handler 处理超限 ----
    from app.core.ratelimit import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ---- 全局 ProblemDetail exception handlers (SPEC §4.3). 兜底绝不回栈. ----
    @app.exception_handler(DomainError)
    async def _domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        log.warning("domain_error", title=exc.title, detail=exc.detail)
        return _problem(request, status_code=exc.status, title=exc.title, detail=exc.detail)

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return _problem(request, status_code=exc.status_code, title="HTTP error", detail=detail)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        detail = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        return _problem(
            request, status_code=422, title="Validation error", detail=detail or "请求体校验失败"
        )

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # 兜底: 服务端记 full stack, 对外绝不回栈.
        log.exception("unhandled_error", error=str(exc))
        return _problem(
            request,
            status_code=500,
            title="Internal error",
            detail="服务内部错误, 已记录; 请联系运维并提供 request_id",
        )

    # ---- /token: 颁发 JWT (SPEC §4.2). demo test user. ----
    @app.post(
        "/token",
        tags=["auth"],
        summary="换取访问令牌 (OAuth2 password grant)",
        status_code=status.HTTP_200_OK,
        responses={
            401: {"description": "凭据错误", "model": ProblemDetail},
        },
    )
    async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> dict[str, object]:
        token = authenticate_and_issue(form.username, form.password)
        if token is None:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        return {"access_token": token, "token_type": "bearer"}

    # ---- 路由挂载 ----
    app.include_router(health.router)
    app.include_router(market.router)
    app.include_router(bids.router)
    app.include_router(clearing.router)
    app.include_router(settlement.router)
    app.include_router(forecast.router)
    app.include_router(backtest.router)
    app.include_router(stream.router)

    return app


app = create_app()
