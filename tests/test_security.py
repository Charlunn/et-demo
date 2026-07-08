"""安全测试 (SPEC §6): 无 token→401; scope 不足→403; SECRET_KEY 默认值+prod 启动 fail."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_no_token_401(client: TestClient):
    r = client.get("/units")
    assert r.status_code == 401


def test_backtest_no_scope_403(client: TestClient):
    # 颁发一个无 scope 的 token (直接构造) -> 应 403.
    from app.core.security import create_access_token

    token = create_access_token(username="trader", scopes=[], expires_minutes=5)
    r = client.post(
        "/backtest",
        headers={"Authorization": f"Bearer {token}"},
        json={"days": 1, "model": "persistence"},
    )
    assert r.status_code == 403
    body = r.json()
    assert body["title"] == "Forbidden"
    assert "backtest:run" in body["detail"]


def test_backtest_with_scope_passes(client: TestClient, auth_headers):
    r = client.post("/backtest", headers=auth_headers, json={"days": 1, "model": "persistence"})
    assert r.status_code == 200


def test_invalid_token_401(client: TestClient):
    r = client.get("/units", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_bad_credentials_401(client: TestClient):
    r = client.post("/token", data={"username": "trader", "password": "wrong"})
    assert r.status_code == 401


def test_secret_key_failfast_in_prod(monkeypatch):
    # SPEC §4.1: debug=false + 默认占位 SECRET_KEY -> 启动拒.
    import os

    env = {
        **os.environ,
        "DEBUG": "false",
        "SECRET_KEY": "dev-only-do-not-use-in-production-please-change-me-32chars-min",
    }
    monkeypatch.setattr(os, "environ", env)
    from app.core.config import Settings

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings()


def test_secret_key_too_short_in_prod(monkeypatch):
    import os

    env = {**os.environ, "DEBUG": "false", "SECRET_KEY": "short"}
    monkeypatch.setattr(os, "environ", env)
    from app.core.config import Settings

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings()


def test_cors_wildcard_rejected(monkeypatch):
    # SPEC §4.5 / main.py: create_app 在 CORS allowlist 含 '*' 时直接拒 (与 debug 无关).
    import os

    import app.main as main_mod
    from app.core.config import Settings

    monkeypatch.setattr(
        os,
        "environ",
        {
            **os.environ,
            "DEBUG": "true",
            "CORS_ORIGINS": '["*"]',
            "DATABASE_URL": "sqlite+aiosqlite:///./spark-test.db",
        },
    )
    s = Settings()
    monkeypatch.setattr(main_mod, "settings", s)
    with pytest.raises(RuntimeError, match="CORS"):
        main_mod.create_app()
