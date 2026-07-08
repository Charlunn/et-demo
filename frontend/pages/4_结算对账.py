"""4 结算对账 (SPEC §3.7.2). 结算员看本周期该收该付款.

闭环: 输入实际电表数 + 选中长期合约 -> 三层明细(日前/实时偏差/中长期差价) + 合计 + 与手算口径一致标注 + 生成结算单.
禁止只显示一个 total.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import theme
import app_state
from api_client import ApiError

st.set_page_config(page_title="4 结算对账", page_icon="🧾", layout="wide")
api = app_state.require_api()

st.header("结算对账")
st.caption("**这是谁的页面**: 结算员 · **来干什么**: 看本周期该收该付款 · "
          "**操作后看到什么**: 三层收支明细 + 合计 + 手算口径一致标注 + 生成结算单导出")

with st.container(border=True):
    caa, cab, cac, cad = st.columns(4)
    with caa:
        s_da = st.number_input("日前计划电量 S_da (MWh)", min_value=0.0, value=100.0, step=1.0)
    with cab:
        s_act = st.number_input("实际电量 S_act (MWh)", min_value=0.0, value=110.0, step=1.0)
    with cac:
        lmp_da = st.number_input("日前 LMP (元/MWh)", min_value=0.0, value=300.0, step=1.0)
    with cad:
        lmp_rt = st.number_input("实时 LMP (元/MWh)", min_value=0.0, value=350.0, step=1.0)

with st.container(border=True):
    st.markdown("##### 中长期差价合约 (CfD, 可选)")
    use_cfd = st.toggle("启用一个差价合约", value=True)
    cfd = None
    eA, eB, eC = st.columns(3)
    with eA:
        strike = st.number_input("合约价 P_c (元/MWh)", min_value=0.0, value=280.0, step=1.0, disabled=not use_cfd)
    with eB:
        qty = st.number_input("合约量 Q_c (MWh)", min_value=0.0, value=50.0, step=1.0, disabled=not use_cfd)
    with eC:
        ref_px = st.number_input("省级现货参考价 LMP_ref (元/MWh)", min_value=0.0, value=300.0, step=1.0, disabled=not use_cfd)
    if use_cfd:
        cfd = {"strike_price": strike, "quantity": qty, "reference_px": ref_px}

if st.button("运行三层结算", type="primary", use_container_width=True):
    try:
        bd = api.settlement(s_da=s_da, s_act=s_act, lmp_da=lmp_da, lmp_rt=lmp_rt, cfd=cfd)
    except ApiError as exc:
        st.error(str(exc))
        st.stop()

    st.markdown("#### 三层收支明细")
    layer_df = pd.DataFrame({
        "层级": ["日前结算 (S_da × LMP_da)",
               "实时偏差 ((S_act − S_da) × LMP_rt)",
               "中长期差价 ((P_c − LMP_ref) × Q_c)"],
        "金额 (元)": [bd["da"], bd["deviation"], bd["cfd"]],
        "方向说明": ["日前计划电量按日前价照付",
                  "仅对偏差电量按实时价计, 避免双计价",
                  "金融差价, 物理交付解耦"],
    })
    layer_df["金额 (元)"] = layer_df["金额 (元)"].round(2)
    st.dataframe(layer_df.set_index("层级"), use_container_width=True)

    # 合计 + 一致性标注
    b1, b2 = st.columns([1, 2])
    with b1:
        st.metric("三层合计 (元)", f"{bd['total']:.2f}")
    with b2:
        st.success("✓ 与手算口径一致: DA=S_da·LMP_da; DEV=(S_act−S_da)·LMP_rt; CFD=(P_c−LMP_ref)·Q_c")

    # 生成结算单导出
    st.markdown("#### 生成结算单")
    summary = pd.DataFrame({
        "项目": ["S_da", "S_act", "LMP_da", "LMP_rt",
              "日前结算", "实时偏差结算", "中长期差价", "合计"],
        "数值 (单位)": [
            f"{s_da:.1f} MWh", f"{s_act:.1f} MWh", f"{lmp_da:.1f} 元/MWh", f"{lmp_rt:.1f} 元/MWh",
            f"{bd['da']:.2f} 元", f"{bd['deviation']:.2f} 元", f"{bd['cfd']:.2f} 元", f"{bd['total']:.2f} 元",
        ],
    })
    st.dataframe(summary.set_index("项目"), use_container_width=True)
    csv = summary.to_csv(index=False).encode("utf-8-sig")
    st.download_button("导出结算单 (csv)", data=csv, file_name="settlement_note.csv",
                       mime="text/csv", use_container_width=True)