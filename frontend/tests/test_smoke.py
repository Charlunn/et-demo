"""frontend 测试 (SPEC §6): smoke test, 不点真后端.

streamlit AppTest 验证:
- app.py 可渲染 (登录表单或登录后欢迎语出现)
- 五个业务页均可加载且无异常 (AppTest 以页面路径名识别)
- 解耦后端: app_state.ensure_session 被桩替换为假 Api, 不发网络.
"""
from __future__ import annotations

import pathlib
import sys

from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

# 让 frontend 模块可被 import.
FRONT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FRONT))
import app_state  # noqa: E402


class _FakeApi:
    """桩后端: 返回合成结构, 不发网络. 页面取 session['api'] 即此实例."""

    def __init__(self) -> None:
        self._token = "fake"

    @staticmethod
    def _ts():
        return "2024-01-01T00:00:00"

    @staticmethod
    def _unit(uid="G1"):
        return {"unit_id": uid, "node_id": "REF", "a": 0.02, "b": 20.0, "c": 0.0,
                "p_min": 0.0, "p_max": 120.0, "ramp_up": 60.0, "ramp_down": 60.0, "is_must_run": False}

    def units(self):
        return [self._unit(uid) for uid in ("G1", "G2", "G3")]

    def market(self, node=None, span=96):
        return {"lmp": [{"ts": self._ts(), "node": "REF", "value": 30.0},
                        {"ts": self._ts(), "node": "LOAD", "value": 48.0}],
                "load": [{"ts": self._ts(), "node": "REF", "value": 90.0},
                         {"ts": self._ts(), "node": "LOAD", "value": 150.0}],
                "blocked_periods": [5]}

    def stream(self, node="LOAD", series="lmp", span=96, aggregate_1h=False):
        return [{"ts": self._ts(), "node_id": "LOAD", "series_type": "lmp", "value": 40.0, "quality_flag": "OK"}] * 4

    def submit_bid(self, unit_id, strategy, risk_markup, periods=96):
        return {"unit_id": unit_id, "period": 0, "strategy": strategy,
                "segments": [{"price": 20.0, "mw": 12.0}] * 10, "segment_count": 10}

    def list_bids(self, unit_id):
        return [self.submit_bid(unit_id, "marginal", 0.0)]

    def clearing(self, periods, line_flow_limit_mw, days, use_seed, **kw):
        pr = {"period": 0, "p": {"G1": 100.0}, "r": {"G1": 5.0},
              "lmp": {"REF": 30.0, "LOAD": 48.0},
              "lmp_components": {"REF": {"energy": 30.0, "congestion": 0.0, "loss": 0.0},
                                 "LOAD": {"energy": 30.0, "congestion": 18.0, "loss": 0.0}},
              "line_flow_mw": 80.0, "blocked": True}
        return {"status": "optimal", "total_cost": 1000.0, "periods": [pr] * int(periods)}

    def settlement(self, **kw):
        return {"da": 30000.0, "deviation": 3500.0, "cfd": -1000.0, "total": 32500.0}

    def forecast(self, horizon=96, **kw):
        return {"values": [40.0] * horizon, "model_name": "persistence"}

    def backtest(self, days=1, model=None, line_flow_limit_mw=80.0):
        return {
            "periods": 96, "beats_baseline": True,
            "strategy_baseline": {"name": "marginal", "model_name": "n/a",
                                    "metrics": {"net_pnl": 100.0, "hit_rate": 0.5, "profit_factor": 1.2,
                                                "information_ratio": 0.1, "clearing_mape": 5.0, "max_drawdown": 20.0}},
            "strategy_forecast": {"name": "marginal_plus_forecast", "model_name": "persistence",
                                   "metrics": {"net_pnl": 110.0, "hit_rate": 0.55, "profit_factor": 1.3,
                                               "information_ratio": 0.12, "clearing_mape": 4.5, "max_drawdown": 18.0}},
            "pnl_curve_baseline": [10.0] * 96, "pnl_curve_forecast": [12.0] * 96,
            "summary_zh": "回测小结: 待测胜基线.", "summary_en": "Backtest: forecast beats baseline.",
        }


def _fake_ensure_session():
    st.session_state.api = _FakeApi()
    st.session_state.logged_in = True
    st.session_state.setdefault("node", "LOAD")
    st.session_state.setdefault("unit", "G1")
    st.session_state.setdefault("back_span", 96)
    return st.session_state.api


PAGES = [
    "1_行情看板.py",
    "2_报价工作台.py",
    "3_出清与计划.py",
    "4_结算对账.py",
    "5_回测复盘.py",
]


def test_app_renders_login_or_welcome():
    """app.py 可渲染 (桩后端后登录后欢迎语出现)."""
    with patch.object(app_state, "ensure_session", _fake_ensure_session):
        at = AppTest.from_file(str(FRONT / "app.py"), default_timeout=10).run(timeout=20)
    assert not at.exception
    # 登录后顶部显示欢迎语
    assert any("欢迎" in (m.value or "") or "欢迎" in (m.markdown if hasattr(m, "markdown") else "")
               for m in at.markdown)


def test_five_business_pages_render():
    """五个业务页均可加载且无异常 (假 Api, 不点真后端)."""
    for fname in PAGES:
        with patch.object(app_state, "ensure_session", _fake_ensure_session):
            at = AppTest.from_file(str(FRONT / "pages" / fname), default_timeout=10).run(timeout=30)
        assert not at.exception, f"{fname} 抛异常"
        # 每页有 header 说明这是谁的页面 (SPEC §3.7.1)
        assert at.header


def test_sidebar_navigation_contains_five_pages():
    """pages 目录含五业务页名, 命名按所有 (streamlit 多页按文件名生成侧边导航)."""
    pages_dir = FRONT / "pages"
    names = sorted(p.name for p in pages_dir.glob("*.py"))
    assert names == sorted(PAGES)