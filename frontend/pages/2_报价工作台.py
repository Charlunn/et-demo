"""2 报价工作台 (SPEC §3.7.2). 交易员给手中机组做一份分段报价.

闭环: 选机组 -> 看成本曲线(边际成本线) -> 选策略+风险加成 -> 分段报价表实时重算 -> 提交报价(进队列).
禁止让用户手填 JSON.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import theme
import app_state
from api_client import ApiError

st.set_page_config(page_title="2 报价工作台", page_icon="🧮", layout="wide")
api = app_state.require_api()

st.header("报价工作台")
st.caption("**这是谁的页面**: 交易员 · **来干什么**: 给自己手里的机组做一份分段报价 · "
          "**操作后看到什么**: 选策略自动填报价表; 改风险参数表实时重算; 提交报价进待出清队列")

# 取机组列表
try:
    units = api.units()
except ApiError as exc:
    st.error(str(exc))
    st.stop()

unit_opts = [u["unit_id"] for u in units]
prev = st.session_state.get("unit", "G1")
prev = prev if prev in unit_opts else unit_opts[0]

# ---- 顶部一行: 机组选择 + 策略 + 风险加成 (全部是业务参数, 非调试) ----
with st.container(border=True):
    hc, hs, hr = st.columns([1, 2, 2])
    with hc:
        unit_id = st.selectbox("选择机组", unit_opts, index=unit_opts.index(prev))
        if unit_id != prev:
            st.session_state.unit = unit_id
    with hs:
        strategy = st.select_slider(
            "报价策略",
            options=["marginal", "marginal_plus_forecast"],
            format_func=lambda s: {"marginal": "报边际成本", "marginal_plus_forecast": "边际成本 + 预测加成"}[s],
        )
    with hr:
        risk_markup = st.slider("风险加成 (元/MWh)", 0.0, 50.0, 5.0, step=0.5)

unit = next(u for u in units if u["unit_id"] == unit_id)
st.session_state.unit = unit_id

# ---- 成本曲线 / 边际成本线 (业务含义可视化) ----
p_arr = np.linspace(unit["p_min"], unit["p_max"], 50)
mc = unit["a"] * 2 * p_arr + unit["b"]  # 边际成本 dC/dP = 2aP + b
cost_curve = go.Figure()
cost_curve.add_trace(go.Scatter(x=p_arr, y=mc, mode="lines", name="边际成本", line={"color": theme.BRAND, "width": 2}))
cost_curve.update_layout(margin={"t": 20}, height=260, legend={"orientation": "h", "y": -0.2})
cost_curve.update_xaxes(title_text="出力 P (MW)", gridcolor="#E2E8F0")
cost_curve.update_yaxes(title_text="边际成本 (元/MWh)", gridcolor="#E2E8F0")
st.plotly_chart(cost_curve, use_container_width=True)

# ---- 分段报价表 (≤10 段; 实时重算由后端真出数) ----
try:
    submitted = api.submit_bid(unit_id, strategy, risk_markup, periods=1)
except ApiError as exc:
    st.error(str(exc))
    submitted = None

if submitted:
    seg_df = pd.DataFrame(submitted["segments"])
    seg_df.index = [f"段 {i+1}" for i in range(len(seg_df))]
    seg_df.columns = ["价格 (元/MWh)", "容量 (MW)"]
    bA, bB = st.columns([3, 2])
    with bA:
        st.markdown("**分段报价表** (≤10 段, 由后端按边际成本+策略生成; 前端只呈现)")
        st.dataframe(seg_df.style.format({"价格 (元/MWh)": "{:.1f}", "容量 (MW)": "{:.1f}"}),
                     use_container_width=True, height=300)
    with bB:
        st.metric("机组", unit_id)
        st.metric("段落总数", submitted["segment_count"])
        st.metric("策略", {"marginal": "报边际成本", "marginal_plus_forecast": "边际成本+预测加成"}[strategy])
        st.metric("风险加成", f"{risk_markup:.1f} 元/MWh")

    st.divider()
    # ---- 提交报价进待出清队列 (业务动作闭环) ----
    st.markdown("**提交报价到待出清队列**")
    if st.button("确认提交报价", type="primary", use_container_width=True):
        try:
            done = api.submit_bid(unit_id, strategy, risk_markup, periods=96)
            st.success(f"已提交机组 {unit_id} 的 {done['segment_count']} 段报价 (96 时段) 到待出清队列。")
            # 看一眼当前队列
            q = api.list_bids(unit_id)
            if q:
                st.markdown(f"该机组当前待出清报价数: **{len(q)}**")
        except ApiError as exc:
            st.error(str(exc))