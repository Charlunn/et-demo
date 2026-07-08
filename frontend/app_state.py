"""全局会话态 (SPEC §3.7.1): 在 app.py 与每个业务页可重复调用, 幂等初始化 ApiClient."""
from __future__ import annotations

import streamlit as st

from api_client import ApiClient

_DEFAULTS = {"logged_in": False, "node": "LOAD", "unit": "G1", "back_span": 96}


def ensure_session() -> ApiClient:
    """幂等初始化: 缺 api/各默认值则补. 返回当前 ApiClient (session 里那份)."""
    if "api" not in st.session_state:
        st.session_state.api = ApiClient()
    for k, v in _DEFAULTS.items():
        st.session_state.setdefault(k, v)
    return st.session_state.api


def require_api() -> ApiClient:
    """业务页第一行: 取 ApiClient. 页面据此判定登录态."""
    return ensure_session()