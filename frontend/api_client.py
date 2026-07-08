"""后端 REST 薄封装 (SPEC §3.7.1). 页面唯一调用通道, base_url 从 env, 避免裸 URL/requests.

错误向上抛成业务文案 (非堆栈). 页面 import 此模块, 不自己拼 URL.
"""
from __future__ import annotations

import os

import httpx

# base_url: 后端 API. docker 内通过服务名 backend; 本地 localhost.
_DEFAULT_BASE = os.environ.get("BACKEND_API_URL", "http://localhost:8000")


class ApiError(RuntimeError):
    """业务化 API 错误 (已脱离堆栈)."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class ApiClient:
    """薄 HTTP 客户端. 登录拿 token 后随实例漂带 Authorization 头."""

    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        self.base_url = (base_url or _DEFAULT_BASE).rstrip("/")
        self._token: str | None = None
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def login(self, username: str, password: str) -> None:
        r = self._client.post("/token", data={"username": username, "password": password})
        if r.status_code != 200:
            raise ApiError("登录失败: 请检查用户名/密码", r.status_code)
        self._token = r.json()["access_token"]

    @property
    def authed(self) -> bool:
        return self._token is not None

    def _headers(self) -> dict[str, str]:
        if not self._token:
            raise ApiError("请先登录再操作")
        return {"Authorization": f"Bearer {self._token}"}

    # ---- 业务端点 (对应 SPEC §5) ----
    def units(self) -> list[dict]:
        return self._get("/units")

    def market(self, node: str | None = None, span: int = 96) -> dict:
        params: dict[str, object] = {"span": span}
        if node:
            params["node"] = node
        return self._get("/market", params)

    def stream(self, node: str = "LOAD", series: str = "lmp", span: int = 96, aggregate_1h: bool = False) -> list[dict]:
        return self._get(
            "/stream",
            {"node": node, "series": series, "span": span, "aggregate_1h": aggregate_1h},
        )

    def submit_bid(self, unit_id: str, strategy: str, risk_markup: float, periods: int = 96) -> dict:
        return self._post("/bids", {"unit_id": unit_id, "strategy": strategy,
                                    "risk_markup": risk_markup, "periods": periods})

    def list_bids(self, unit_id: str) -> list[dict]:
        return self._get("/bids", {"unit_id": unit_id})

    def clearing(self, periods: int, line_flow_limit_mw: float, days: int, use_seed: bool,
                 *, load_ref: list[float] | None = None, load_load: list[float] | None = None) -> dict:
        body = {"periods": periods, "line_flow_limit_mw": line_flow_limit_mw,
                "days": days, "use_seed": use_seed,
                "load_ref": load_ref or [100.0], "load_load": load_load or [150.0]}
        return self._post("/clearing", body)

    def settlement(self, s_da: float, s_act: float, lmp_da: float, lmp_rt: float,
                   cfd: dict | None = None) -> dict:
        body = {"s_da": s_da, "s_act": s_act, "lmp_da": lmp_da, "lmp_rt": lmp_rt, "cfd": cfd}
        return self._post("/settlement", body)

    def forecast(self, horizon: int = 96, model_name: str | None = None, seed_days: int = 2,
                 target_node: str = "LOAD") -> dict:
        body = {"horizon": horizon, "model_name": model_name, "seed_days": seed_days, "target_node": target_node}
        return self._post("/forecast", body)

    def backtest(self, days: int = 1, model: str | None = None,
                 line_flow_limit_mw: float = 80.0) -> dict:
        body = {"days": days, "model": model, "line_flow_limit_mw": line_flow_limit_mw}
        return self._post("/backtest", body)

    # ---- internals ----
    def _get(self, path: str, params: dict | None = None) -> object:
        try:
            r = self._client.get(path, params=params, headers=self._headers())
        except httpx.HTTPError as exc:
            raise ApiError(f"网络错误: 后端不可达 ({exc.__class__.__name__})") from exc
        return self._unwrap(r)

    def _post(self, path: str, body: dict) -> object:
        try:
            r = self._client.post(path, json=body, headers=self._headers())
        except httpx.HTTPError as exc:
            raise ApiError(f"网络错误: 后端不可达 ({exc.__class__.__name__})") from exc
        return self._unwrap(r)

    def _unwrap(self, r: httpx.Response) -> object:
        if 200 <= r.status_code < 300:
            return r.json()
        # ProblemDetail -> 抽 detail 字段做业务文案
        try:
            d = r.json()
            msg = d.get("detail") or d.get("title") or "后端返回错误"
        except ValueError:
            msg = f"后端返回非 JSON ({r.status_code})"
        raise ApiError(msg, r.status_code)