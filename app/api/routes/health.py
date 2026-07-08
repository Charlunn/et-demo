"""健康端点 (SPEC §5): /healthz 存活, /readyz 依赖探测."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger

router = APIRouter(tags=["health"])
log = get_logger(__name__)


@router.get("/healthz", status_code=status.HTTP_200_OK, summary="存活探针")
async def healthz() -> dict[str, str]:
    """存活探针: 不检查依赖, 仅进程存活即 200."""
    return {"status": "ok", "app": settings.app_name}


@router.get("/readyz", status_code=status.HTTP_200_OK, summary="就绪探针")
async def readyz() -> JSONResponse:
    """就绪探针: 探测数据库依赖 (懒连接, 失败不炸进程但降级返回)."""
    checks: dict[str, str] = {"db": "ok"}
    ready = True
    try:
        # 延迟导入以避免在骨架阶段强依赖 db 模块就绪.
        from app.db.session import check_db

        await check_db()
    except Exception as exc:  # noqa: BLE001 - 探针不应把异常抛给探针调用方
        ready = False
        checks["db"] = f"degraded: {type(exc).__name__}"
        log.warning("readyz_db_degraded", error=str(exc))
    code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content={"ready": ready, **checks})