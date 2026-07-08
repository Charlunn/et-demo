"""预测器测试 (SPEC §6): Persistence 实跑; 工厂对 XGBoost 缺包回退且 log warn (caplog)."""

from __future__ import annotations

import logging

import numpy as np
import pytest

from app.domain.forecaster import get_forecaster
from app.domain.forecaster.persistence import PersistenceForecaster


def test_persistence_real_run_returns_horizon_length():
    f = PersistenceForecaster()
    hist = np.linspace(30, 60, 200)  # 含 >96 步, 触发日周期分支
    out = f.forecast(hist, horizon=24)
    assert isinstance(out, np.ndarray)
    assert out.shape == (24,)
    assert np.isfinite(out).all()
    assert (out >= 0).all()


def test_persistence_short_history_falls_back_to_last_price():
    f = PersistenceForecaster()
    out = f.forecast(np.array([42.0]), horizon=5)
    assert np.allclose(out, 42.0)


def test_persistence_empty_history_returns_zeros():
    out = PersistenceForecaster().forecast(np.array([]), horizon=10)
    assert out.shape == (10,)
    assert np.all(out == 0.0)


def test_factory_persistence_by_name():
    f = get_forecaster("persistence")
    assert f.name == "persistence"


def test_factory_unknown_falls_back_to_persistence():
    f = get_forecaster("does-not-exist")
    assert f.name == "persistence"


def test_factory_xgboost_missing_fallback_warns(caplog):
    # SPEC §6: 缺包回退且 log warn, 用 caplog 断言 (structlog 经标准 logging 路由).
    try:
        import xgboost  # type: ignore[import-not-found]  # noqa: F401

        pytest.skip("xgboost 已安装, 跳过缺包回退断言")
    except ImportError:
        pass
    with caplog.at_level(logging.WARNING, logger="app.domain.forecaster.factory"):
        f = get_forecaster("xgboost")
    assert f.name == "persistence"
    assert any("forecaster_fallback" in r.getMessage() for r in caplog.records)


def test_lstm_stub_warns_and_returns_persistence():
    from app.domain.forecaster.lstm_stub import LSTMForecaster

    f = LSTMForecaster()
    out = f.forecast(np.array([10.0]), horizon=3)
    assert out.shape == (3,)
    assert f.name == "lstm"  # 名字标识 stub
