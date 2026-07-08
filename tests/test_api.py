"""API 端点测试 (SPEC §6): happy / 422 / 401 / 404 + ProblemDetail 形状."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _is_problem(d: dict) -> bool:
    # RFC7807 形状 (SPEC §4.3).
    return all(k in d for k in ("type", "title", "status", "detail", "instance", "request_id"))


# ---- happy ----
def test_units_happy(client: TestClient, auth_headers):
    r = client.get("/units", headers=auth_headers)
    assert r.status_code == 200
    units = r.json()
    assert len(units) == 5
    assert {u["unit_id"] for u in units} == {"G1", "G2", "G3", "G4", "G5"}


def test_market_happy(client: TestClient, auth_headers):
    r = client.get("/market?span=24", headers=auth_headers)
    assert r.status_code == 200
    mv = r.json()
    assert "lmp" in mv and "load" in mv and "blocked_periods" in mv


def test_bids_happy(client: TestClient, auth_headers):
    r = client.post(
        "/bids",
        headers=auth_headers,
        json={"unit_id": "G1", "strategy": "marginal", "risk_markup": 5.0, "periods": 1},
    )
    assert r.status_code == 201
    bc = r.json()
    assert bc["unit_id"] == "G1" and bc["segment_count"] == 10
    # fetch queue
    r2 = client.get("/bids?unit_id=G1", headers=auth_headers)
    assert r2.status_code == 200 and len(r2.json()) >= 1


def test_clearing_happy(client: TestClient, auth_headers):
    r = client.post(
        "/clearing",
        headers=auth_headers,
        json={
            "periods": 96,
            "line_flow_limit_mw": 80.0,
            "days": 1,
            "use_seed": True,
            "load_ref": [100.0],
            "load_load": [150.0],
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "optimal"
    assert len(out["periods"]) == 96
    pr = out["periods"][0]
    assert set(pr["lmp_components"]["LOAD"].keys()) == {"energy", "congestion", "loss"}


def test_settlement_happy(client: TestClient, auth_headers):
    r = client.post(
        "/settlement",
        headers=auth_headers,
        json={
            "s_da": 100.0,
            "s_act": 110.0,
            "lmp_da": 300.0,
            "lmp_rt": 350.0,
            "cfd": {"strike_price": 280.0, "quantity": 50.0, "reference_px": 300.0},
        },
    )
    assert r.status_code == 200
    bd = r.json()
    assert abs(bd["da"] - 30000.0) < 1e-3
    assert abs(bd["deviation"] - 3500.0) < 1e-3
    assert abs(bd["cfd"] - -1000.0) < 1e-3
    assert abs(bd["total"] - 32500.0) < 1e-3


def test_forecast_happy(client: TestClient, auth_headers):
    r = client.post(
        "/forecast", headers=auth_headers, json={"horizon": 24, "model_name": "persistence"}
    )
    assert r.status_code == 200
    out = r.json()
    assert len(out["values"]) == 24 and out["model_name"] == "persistence"


def test_backtest_happy(client: TestClient, auth_headers):
    r = client.post("/backtest", headers=auth_headers, json={"days": 1, "model": "persistence"})
    assert r.status_code == 200
    rep = r.json()
    assert rep["periods"] == 96 and rep["beats_baseline"] is True


def test_stream_happy(client: TestClient, auth_headers):
    r = client.get("/stream?node=LOAD&series=lmp&span=8", headers=auth_headers)
    assert r.status_code == 200
    ticks = r.json()
    assert len(ticks) == 8


# ---- 401 (无 token) ----
def test_units_requires_auth(client: TestClient):
    r = client.get("/units")
    assert r.status_code == 401
    assert _is_problem(r.json())


# ---- 404 ----
def test_bids_unit_not_found(client: TestClient, auth_headers):
    r = client.post(
        "/bids",
        headers=auth_headers,
        json={"unit_id": "NOPE", "strategy": "marginal", "risk_markup": 0.0},
    )
    assert r.status_code == 404
    assert _is_problem(r.json()) and r.json()["title"] == "Not found"


# ---- 422 (校验) ----
def test_bids_validation_rejects_negative_markup(client: TestClient, auth_headers):
    r = client.post(
        "/bids",
        headers=auth_headers,
        json={"unit_id": "G1", "strategy": "marginal", "risk_markup": -5.0},
    )
    assert r.status_code == 422
    assert _is_problem(r.json())


def test_clearing_validation(client: TestClient, auth_headers):
    r = client.post(
        "/clearing",
        headers=auth_headers,
        json={
            "periods": 0,
            "line_flow_limit_mw": 80.0,
            "days": 1,
            "use_seed": True,
            "load_ref": [],
            "load_load": [],
        },
    )
    assert r.status_code == 422


# ---- ProblemDetail 形状 (SPEC §4.3) ----
def test_problem_detail_shape_on_404(client: TestClient, auth_headers):
    r = client.post(
        "/bids",
        headers=auth_headers,
        json={"unit_id": "NOPE", "strategy": "marginal", "risk_markup": 0.0},
    )
    body = r.json()
    assert body["type"] == "about:blank"
    assert body["status"] == r.status_code
    assert body["instance"] == "/bids"
    assert isinstance(body["request_id"], str) and len(body["request_id"]) > 0
