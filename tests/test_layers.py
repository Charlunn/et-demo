"""分层与 import 级别约束测试 (SPEC §6): import-linter 等价, 静态断言.

- app/api/** 不导 app.models / sqlalchemy (路由薄, 不碰 ORM).
- app/services/** 不导 fastapi (service 纯函数, 不碰 HTTP 类型).
- app/domain/** 不导 fastapi / sqlalchemy / httpx (无 IO, 最易测).
"""

from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent / "app"


def _imports_in(file: pathlib.Path) -> set[str]:
    tree = ast.parse(file.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
            if node.level == 0:
                mods.add(node.module)
    return mods


def _py_files(pkg: str) -> list[pathlib.Path]:
    base = ROOT / pkg
    return list(base.rglob("*.py"))


def test_api_routes_no_sqlalchemy_no_app_models():
    bad = []
    for f in _py_files("api"):
        imps = _imports_in(f)
        if "sqlalchemy" in imps or any(m == "app.models" for m in imps):
            bad.append(str(f))
    assert not bad, f"api routes should not import sqlalchemy/app.models: {bad}"


def test_services_no_fastapi():
    bad = []
    for f in _py_files("services"):
        if "fastapi" in _imports_in(f):
            bad.append(str(f))
    assert not bad, f"services should not import fastapi: {bad}"


def test_domain_no_io_libraries():
    bad = []
    for f in _py_files("domain"):
        imps = _imports_in(f)
        if {"fastapi", "sqlalchemy", "httpx"} & imps:
            bad.append(str(f))
    assert not bad, f"domain should not import fastapi/sqlalchemy/httpx: {bad}"
