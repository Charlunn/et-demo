"""5 回测复盘 (SPEC §3.7.2). 分析师/交易员跑两条策略对比业绩.

闭环: 选历史区间 + 选两条策略 -> 运行 -> 双 PnL 累计曲线对照 + 指标6项对照表 + 中文小结 + 导出复盘报告.
禁止让用户去 JSON 里找指标.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import theme
import app_state
from api_client import ApiError

st.set_page_config(page_title="5 回测复盘", page_icon="📊", layout="wide")
api = app_state.require_api()

st.header("回测复盘")
st.caption("**这是谁的页面**: 分析师 / 交易员 · **来干什么**: 跑两条策略对比业绩 · "
          "**操作后看到什么**: 双 PnL 累计曲线 + 指标6项对照表 + 中文自然语言小结 + 导出复盘报告")

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        days = st.select_slider("回测天数 (1天=96时段)", options=[1, 2, 3, 5], value=1)
    with c2:
        line_limit = st.slider("线路潮流上限 (MW)", 10.0, 200.0, 80.0, step=10.0)
    with c3:
        model = st.selectbox("待测策略的预测模型",
                              ["persistence", "xgboost", "lstm"],
                              index=0,
                              help="persistence 真跑; xgboost 缺包回退 persistence; lstm 仅 stub")
    run = st.button("运行回测", type="primary", use_container_width=True)

if "backtest_report" not in st.session_state:
    st.session_state.backtest_report = None

if run or st.session_state.backtest_report is None:
    if not run and st.session_state.backtest_report is None:
        st.info("点上方 **运行回测**, 对比 报边际成本(基线) vs 边际成本+预测加成(待测)。")
        st.stop()
    try:
        with st.spinner("回放合成历史, 跑两条策略..."):
            st.session_state.backtest_report = api.backtest(days=days, model=model,
                                                            line_flow_limit_mw=line_limit)
    except ApiError as exc:
        st.error(str(exc))
        st.stop()

rep = st.session_state.backtest_report
base = rep["strategy_baseline"]["metrics"]
fc = rep["strategy_forecast"]["metrics"]

# ---- 双 PnL 累计曲线 ----
cum_base = pd.Series(rep["pnl_curve_baseline"]).cumsum()
cum_fc = pd.Series(rep["pnl_curve_forecast"]).cumsum()
fig = go.Figure()
fig.add_trace(go.Scatter(y=cum_base, name=f"基线 · {rep['strategy_baseline']['name']}",
                         line={"color": theme.NEUTRAL_MID, "width": 2}))
fig.add_trace(go.Scatter(y=cum_fc, name=f"待测 · {rep['strategy_forecast']['name']}",
                         line={"color": theme.BRAND, "width": 2.5}))
fig.update_layout(margin={"t": 20}, height=340, legend={"orientation": "h", "y": -0.2})
fig.update_yaxes(title_text="累计 PnL (元)", gridcolor="#E2E8F0")
fig.update_xaxes(title_text="时段")
st.plotly_chart(fig, use_container_width=True)

verdict = "胜" if rep["beats_baseline"] else "不及"
vcol = theme.MONEY_POS if rep["beats_baseline"] else theme.MONEY_NEG
st.markdown(f"<h4 style='color:{vcol}'>待测策略 {verdict} 基线 — 净收益 {fc['net_pnl']:.1f} 元 vs 基线 {base['net_pnl']:.1f} 元</h4>",
            unsafe_allow_html=True)

# ---- 指标6项对照表 (禁止去 JSON 里找) ----
st.markdown("#### 六项指标对照表")
metric_rows = [
    ("总收益 (元)", "net_pnl"),
    ("命中率", "hit_rate"),
    ("盈亏比 (profit_factor)", "profit_factor"),
    ("信息比率 (年化 Sharpe)", "information_ratio"),
    ("出清价 MAPE %", "clearing_mape"),
    ("最大回撤 (元)", "max_drawdown"),
]
rows = []
for label, key in metric_rows:
    bv = base[key]
    fv = fc[key]
    if key == "hit_rate":
        bv = f"{bv:.3f}"
        fv = f"{fv:.3f}"
    rows.append({"指标": label, "基线": bv, "待测": fv})
mtab = pd.DataFrame(rows)
st.dataframe(mtab.set_index("指标"), use_container_width=True)

# ---- 中文自然语言小结 (程序生成, 诚实标注哪些真跑哪些 stub) ----
with st.container(border=True):
    st.markdown("#### 中文自然语言小结 (程序生成, 诚实标注)")
    st.write(rep["summary_zh"])
    with st.expander("英文小结"):
        st.write(rep["summary_en"])

# ---- 导出复盘报告 ----
st.markdown("#### 导出复盘报告")
report_csv = pd.DataFrame({
    "field": ["periods", "beats_baseline", "baseline_net_pnl", "forecast_net_pnl", "model_used", "summary_zh"],
    "value": [rep["periods"], rep["beats_baseline"], base["net_pnl"], fc["net_pnl"],
              rep["strategy_forecast"]["model_name"], rep["summary_zh"]],
})
st.download_button("导出复盘报告 (csv)", data=report_csv.to_csv(index=False).encode("utf-8-sig"),
                   file_name="backtest_report.csv", mime="text/csv", use_container_width=True)