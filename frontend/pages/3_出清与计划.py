"""3 出清与计划 (SPEC §3.7.2). 调度/交易 触发或查看本次出清与每机组出力计划.

闭环: 点运行出清 -> 每节点 LMP 卡片(能量/阻塞/损耗) + 每机组 P/R + 阻塞可视化 + 时段下钻.
禁止只甩一坨调度结果 JSON.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import theme
import app_state
from api_client import ApiError

st.set_page_config(page_title="3 出清与计划", page_icon="⚙️", layout="wide")
api = app_state.require_api()

st.header("出清与计划")
st.caption("**这是谁的页面**: 调度 / 交易 · **来干什么**: 触发或查看本次出清与每机组出力计划 · "
          "**操作后看到什么**: 每节点 LMP(能量价/阻塞价/损耗价) + 每机组 P/R + 阻塞可视化 + 时段下钻")

with st.container(border=True):
    pc, lc, dc, bc = st.columns(4)
    with pc:
        periods = st.select_slider("时段数", options=[24, 48, 96], value=96)
    with lc:
        line_limit = st.slider("线路潮流上限 (MW)", 10.0, 200.0, 80.0, step=10.0)
    with dc:
        days = st.select_slider("数据来源天数", options=[1, 2, 3], value=1)
    with bc:
        run = st.button("运行出清", type="primary", use_container_width=True)

if "clearing_result" not in st.session_state:
    st.session_state.clearing_result = None

if st.session_state.clearing_result is None or run:
    if st.session_state.clearing_result is None and not run:
        st.info("点上方 **运行出清** 跑一次日前联合出清 (能量 + 1 个旋转备用)。")
        st.stop()
    try:
        with st.spinner("求解 LP (能量 + 旋转备用 联合出清)..."):
            st.session_state.clearing_result = api.clearing(periods, line_limit, days, use_seed=True)
    except ApiError as exc:
        st.error(str(exc))
        st.stop()

res = st.session_state.clearing_result
periods_data = res["periods"]
nT = len(periods_data)

# ---- 每节点 LMP 拆解卡片 (取整段代表性时段: 最末时段) ----
last = periods_data[-1]
st.markdown("#### 出清结果 · 末时段 LMP 拆解 (节点能量价 / 阻塞价 / 损耗价)")
cells = st.columns(len(last["lmp"]))
for i, (node, lmp) in enumerate(last["lmp"].items()):
    comp = last["lmp_components"][node]
    with cells[i]:
        st.markdown(f"`节点 {node}`")
        st.metric("LMP (元/MWh)", f"{lmp:.1f}")
        st.caption(f"能量 {comp['energy']:.1f} · 阻塞 {comp['congestion']:.1f} · 损耗 {comp['loss']:.1f}")

total_p = sum(last["p"].values())
st.metric("末时段总出力 (MW)", f"{total_p:.1f}", help="Σ 各机组 P")

st.markdown("#### 阻塞可视化 (2 节点拓扑, 限流线标红)")
# 简单 2 节点拓扑图: REF --|F|--> LOAD, F 达限时线变红
flow = last["line_flow_mw"]
blocked = last["blocked"]
line_color = theme.BLOCKED_RED if blocked else theme.NEUTRAL_MID
fig = go.Figure()
fig.add_trace(go.Scatter(x=[1, 2], y=[0, 0], mode="markers+text",
                         text=["REF", "LOAD"], textposition="top center",
                         marker={"size": 24, "color": theme.BRAND}))
line_width = 4 if blocked else 2
fig.add_trace(go.Scatter(x=[1.1, 1.9], y=[0, 0], mode="lines",
                         line={"color": line_color, "width": line_width},
                         name=f"潮流 F={flow:.1f} MW" + (" (满载, 阻塞!)" if blocked else "")))
fig.add_annotation(x=1.5, y=0.15, text=f"F = {flow:.1f} MW\n(|F| ≤ {line_limit:.0f})",
                  showarrow=False, font={"color": line_color})
fig.update_xaxes(range=[0.5, 2.5], visible=False)
fig.update_yaxes(range=[-0.5, 0.6], visible=False)
fig.update_layout(margin={"t": 10, "b": 10}, height=180, showlegend=False)
st.plotly_chart(fig, use_container_width=True)
nb = sum(1 for p in periods_data if p["blocked"])
st.info(f"全部 {nT} 时段中, 阻塞(线路满载)时段 **{nb}** 个。")

st.markdown("#### 每机组出力 P 与旋转备用 R (末时段)")
unit_ids = list(last["p"].keys())
sched = pd.DataFrame({
    "机组": unit_ids,
    "出力 P (MW)": [round(last["p"][u], 1) for u in unit_ids],
    "旋转备用 R (MW)": [round(last["r"][u], 1) for u in unit_ids],
})
st.dataframe(sched.set_index("机组"), use_container_width=True)

st.markdown("#### 时段下钻")
sel = st.slider("选择某时段查看 LMP 与机组调度", 0, nT - 1, nT - 1)
pr = periods_data[sel]
st.dataframe(pd.DataFrame({
    "LMP(REF)": [round(pr["lmp"]["REF"], 2)],
    "LMP(LOAD)": [round(pr["lmp"]["LOAD"], 2)],
    "阻塞价": [round(pr["lmp_components"]["LOAD"]["congestion"], 2)],
    "潮流 MW": [round(pr["line_flow_mw"], 2)],
    "阻塞": [pr["blocked"]],
}))
st.line_chart(pd.DataFrame({
    "LMP-REF": [p["lmp"]["REF"] for p in periods_data],
    "LMP-LOAD": [p["lmp"]["LOAD"] for p in periods_data],
}))