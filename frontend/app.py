"""spark-pricing · Streamlit 产品工作台入口 (SPEC §3.7).

判准 (作者与执行 agent 须背记): 这是给电力交易员/分析师用的产品工作台, 不是 API 调试器.
每页是一个业务动作的闭环 (选业务对象 -> 看业务含义的可视化 -> 改业务参数 -> 看业务结果).
页面里禁止裸 URL / requests.post / 让用户手填 JSON.

五个业务页 (streamlit 多页自动生成侧边导航, 见 pages/):
  1 行情看板   2 报价工作台   3 出清与计划   4 结算对账   5 回测复盘

本文件: 登录 + 全局会话态 (token/选中节点/机组/区间) + 顶部状态徽标.
"""
from __future__ import annotations

import streamlit as st

import app_state
import theme
from api_client import ApiClient, ApiError

st.set_page_config(
    page_title="spark-pricing · 电力现货交易工作台",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _init_state() -> None:
    app_state.ensure_session()


_init_state()
api: ApiClient = st.session_state.api


def _login_block() -> None:
    st.markdown(f"<h2 style='color:{theme.BRAND}'>登录 · spark-pricing 电力现货交易工作台</h2>",
                unsafe_allow_html=True)
    st.caption("demo 凭据: trader / trader-secret  (本地后端 :8000 / docker 服务名 backend)")
    with st.form("login"):
        u = st.text_input("用户名", value="trader")
        p = st.text_input("密码", value="trader-secret", type="password")
        if st.form_submit_button("登录", type="primary", use_container_width=True):
            try:
                api.login(u, p)
                st.session_state.logged_in = True
                st.success("登录成功, 左侧选择业务页开始工作.")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))


def _top_bar() -> None:
    userlbl = "trader" if st.session_state.logged_in else "未登录"
    data_badge = "合成数据"  # SPEC §3.7.1: 数据"合成/已同步"状态徽标; 这里恒为合成
    cols = st.columns([6, 2, 2])
    with cols[1]:
        st.markdown(f"`👤 {userlbl}`")
    with cols[2]:
        st.markdown(f"`🧪 {data_badge}`")
    st.divider()


if not st.session_state.logged_in:
    _top_bar()
    _login_block()
    st.stop()

_top_bar()
st.markdown(
    f"欢迎, **trader**。请在**左侧**选择业务页:  "
    f"行情看板 · 报价工作台 · 出清与计划 · 结算对账 · 回测复盘。"
)
st.caption("数据来源: 可复现合成行情 (固定 seed), 非真实平台对接 — 后端为唯一数值来源, 前端只呈现与收集参数。")