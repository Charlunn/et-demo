"""品牌与排版常量 (SPEC §3.7.1). 单主色 + 2 中性辅色; LMP 折线配MP色板 ≤5."""
from __future__ import annotations

# 品牌主色 (电力青绿) + 中性辅色. 节点/序列配色 ≤5, 不彩虹.
BRAND = "#0F8B6C"            # 主色
NEUTRAL_DARK = "#1F2A2E"     # 深文字
NEUTRAL_MID = "#6B7B82"      # 中性辅色
NEUTRAL_LIGHT = "#EFF3F1"    # 浅背景/分隔

# 节点/序列折线配色 (REF / LOAD); 阻塞红标 (SPEC §3.7: 节点阻塞高亮红边).
SERIES_COLORS = ["#0F8B6C", "#2B6CB0", "#B7791F", "#9B2C2C", "#553C9B"]
BLOCKED_RED = "#C53030"
MONEY_NEG = "#C53030"  # 负金额
MONEY_POS = "#0F8B6C"  # 正金额

# KPI / 标题样式 hint
SECTION_FONT = "Inter, sans-serif"