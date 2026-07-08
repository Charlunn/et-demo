"""1 行情看板 (SPEC §3.7.2). 交易员/分析师看当前电价 & 历史走势.

页面闭环: 选节点/时段范围 -> 多节点 LMP 折线 + 负荷日内分布 + 阻塞标记 ->  导出本段行情 csv.
禁止返回原始 JSON.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots
import plotly.graph_objects as go

import theme
import app_state
from api_client import ApiError

st.set_page_config(page_title="1 行情看板", page_icon="📈", layout="wide")
api = app_state.require_api()

st.header("行情看板")
st.caption("**这是谁的页面**: 交易员/分析师 · **来干什么**: 看当前电价 & 历史走势 · "
          "**操作后看到什么**: 多节点 LMP 折线 + 负荷日内分布 + 阻塞时段高亮")

# ---- 业务参数 (非调试器: 页面只收集业务参数) ----
with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        node = st.selectbox("节点", ["REF", "LOAD", "全部"], index=0)
    with c2:
        span = st.slider("时段范围 (15-min 步)", 24, 288, 96, step=24)

node_param = None if node == "全部" else node
try:
    mv = api.market(node=node_param, span=span)
except ApiError as exc:
    st.error(str(exc))
    st.stop()

lmp = mv["lmp"]
load = mv["load"]
blocked = mv["blocked_periods"]

lmp_df = pd.DataFrame(lmp)
load_df = pd.DataFrame(load)

# ---- 三列 KPI (取自选中范围) ----
if len(lmp_df):
    vals = lmp_df["value"].to_numpy()
    b1, b2, b3 = st.columns(3)
    b1.metric(label="区间均价 (元/MWh)", value=f"{vals.mean():.1f}")
    b2.metric(label="区间最高价", value=f"{vals.max():.1f}")
    b3.metric(label="区间最低价", value=f"{vals.min():.1f}")
    b4, b5, b6 = st.columns(3)
    b4.metric("本段时段数", f"{len(lmp_df)}")
    b5.metric("出现的阻塞时段数", f"{len(blocked)}")
    if blocked:
        b6.metric("首个阻塞时段", f"t={blocked[0]}")
    else:
        b6.metric("首个阻塞时段", "—")
else:
    st.info("所选范围无数据")

# ---- 多节点 LMP 折线 (≤5 色) ----
fig = make_subplots(specs=[[{"secondary_y": False}]])
if not lmp_df.empty:
    for i, (n, g) in enumerate(lmp_df.groupby("node")):
        color = theme.SERIES_COLORS[i % len(theme.SERIES_COLORS)]
        fig.add_trace(go.Scatter(x=g["ts"], y=g["value"], name=f"LMP · {n}",
                                 line={"color": color, "width": 2}))
    fig.update_layout(margin={"t": 20}, height=380,
                      legend={"orientation": "h", "y": -0.2})
    fig.update_yaxes(title_text="LMP (元/MWh)", gridcolor="#E2E8F0", gridwidth=1)
    fig.update_xaxes(title_text="时段")
    # 阻塞时段红色竖线高亮 (节点阻塞标记)
    if blocked:
        blk_df = lmp_df["ts"].unique()
        for bi in blocked:
            if bi < len(blk_df):
                fig.add_vline(x=str(blk_df[bi]), line_color=theme.BLOCKED_RED,
                              line_width=1, line_dash="dot", opacity=0.6)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("#### 负荷日内分布 (节点平均)")
if not load_df.empty:
    bar = go.Figure([go.Bar(x=load_df["node"], y=load_df["value"], marker_color=theme.BRAND)])
    bar.update_layout(margin={"t": 10}, height=260, showlegend=False)
    bar.update_yaxes(title_text="负荷 (MW)", gridcolor="#E2E8F0")
    bar.update_xaxes(title_text="节点")
    st.plotly_chart(bar, use_container_width=True)
    if blocked:
        st.warning(f"出现阻塞时段 {len(blocked)} 个 — 负荷节点 LMP 显著高于参考节点, 便宜基荷被线路卡住。")

# ---- 导出本段行情 csv (业务动作闭环) ----
with st.container(border=True):
    st.markdown("**导出本段行情**")
    csv = lmp_df.to_csv(index=False).encode("utf-8-sig") if not lmp_df.empty else b""
    st.download_button("下载 csv", data=csv, file_name=f"lmp_{node}.csv", mime="text/csv",
                       disabled=lmp_df.empty, use_container_width=True)