"""音箱认证 / 授权: JWT(HS256) + OAuth2PasswordBearer + scope 校验 (SPEC §4.2).

- POST /token 颁发 access token (HS256).
- get_current_user Depends 解析 token.
- require_scope("backtest:run") 给敏感写端点.
- 领域错误 UnauthorizedError/ForbiddenError 由全局 handler 统一映射.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Protocol

from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from jose.exceptions import JWTError as JoseJWTError

from app.core.config import settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.logging import get_logger

log = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


class CurrentUser(Protocol):
    username: str
    scopes: list[str]


def _authenticate(username: str, password: str) -> bool:
    # demo-only 密码比对 (SPEC §4.2: 提供一个 dev test user). 生产应走哈希/外部 IdP.
    return username == settings.demo_user and password == settings.demo_password


def create_access_token(
    *,
    username: str,
    scopes: list[str],
    expires_minutes: int | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    payload = {
        "sub": username,
        "scopes": scopes,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def authenticate_and_issue(username: str, password: str) -> str | None:
    """认证成功返回 token, 失败返回 None (由路由映射 401)."""
    if not _authenticate(username, password):
        log.warning("auth_failed", username=username)
        return None
    scopes = [s.strip() for s in settings.demo_scopes.split(",") if s.strip()]
    return create_access_token(username=username, scopes=scopes)


def decode_token(token: str) -> dict[str, object]:
    try:
        payload: dict[str, object] = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
    except (JWTError, JoseJWTError) as exc:
        raise UnauthorizedError("无效或过期的访问令牌") from exc
    return payload


async def get_current_user(token: Annotated[str | None, Depends(oauth2_scheme)]) -> dict[str, object]:
    """解析 Bearer token, 失败抛 401. 所有 user 级端点依赖此函数."""
    if not token:
        raise UnauthorizedError("缺少访问令牌")
    payload = decode_token(token)
    return payload


def require_scope(scope: str):  # type: ignore[no-untyped-def]
    """FastAPI dependency 工厂: 校验当前用户持有指定 scope, 否则 403."""

    async def _checker(user: Annotated[dict[str, object], Depends(get_current_user)]) -> dict[str, object]:
        # scopes 可能是 list[str] (我们颁发的) 或 space-joined str (标准 OAuth).
        raw = user.get("scopes", [])
        if isinstance(raw, str):
            user_scopes = set(raw.split())
        else:
            user_scopes = set(raw)  # type: ignore[arg-type]
        if scope not in user_scopes:
            log.warning("forbidden", username=user.get("sub"), required_scope=scope)
            raise ForbiddenError(f"缺少必要 scope: {scope}")
        return user

    return _checker