# front · spark-pricing 产品工作台 (Streamlit)

> **判准 (SPEC §3.7 + PRD §2.1)**: 这是给**电力交易员/分析师**用的产品工作台, **不是给开发者用的 API 调试器**.
> 交给一个不懂 API 的人, 他能走完 “看行情 → 做报价 → 看出清 → 对账 → 复盘”, 而不是点 “发送请求 / 看 JSON 响应”。

## 五个业务页 (业务 tab, 非技术 tab)

| 页 | 这是谁 | 来干什么 | 看到什么 |
|---|---|---|---|
| 1 行情看板 | 交易员/分析师 | 看当前电价 & 历史走势 | 多节点 LMP 折线 + 负荷日内分布 + 阻塞标记 + 导出 csv |
| 2 报价工作台 | 交易员 | 给机组做分段报价 | 成本曲线 + 分段报价表(≤10段) + 策略/风险加成 + 提交报价 |
| 3 出清与计划 | 调度/交易 | 触发/查看出清与计划 | 每节点 LMP(能量/阻塞/损耗) + 机组 P/R + 阻塞拓扑图 + 时段下钻 |
| 4 结算对账 | 结算员 | 看该收该付款 | 三层明细(日前/实时偏差/中长期差价) + 合计 + 手算口径一致标注 + 结算单导出 |
| 5 回测复盘 | 分析师/交易员 | 跑两策略对比业绩 | 双 PnL 累计曲线 + 指标6项对照表 + 中文小结 + 复盘报告导出 |

## 纪律 (SPEC §3.7.4)
- 页面里**禁止裸 URL / `requests.post` / 让用户手填 JSON**; 后端调用唯一通道是 `api_client.py`.
- 前端不内置领域公式计算, 一切数值来自后端 API (单源真理); 前端只呈现与收集参数.
- 单一品牌主色 + 2 中性辅色 (见 `theme.py` / `.streamlit/config.toml`); 不花哨发光/渐变彩虹.

## 本地跑法
```bash
# 1) 起后端 (在仓库根目录)
uv run python -m app.cli serve --port 8000

# 2) 起前端 (在本目录)
uv venv --python 3.12 .venv
# Windows: .venv\Scripts\ ... 或如下
uv pip install -r requirements.txt
streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
# 浏览器开 http://localhost:8501; demo 登录 trader / trader-secret
```
后端地址由环境变量 `BACKEND_API_URL` 指定 (默认 `http://localhost:8000`).

## docker 跑法
见仓库根目录 `docker-compose.yml` 的 `frontend` 服务:
```bash
docker compose up --build
# 前端 http://localhost:8501  后端 http://localhost:8000
```
docker 内前端经服务名 `backend` 访问 API (`BACKEND_API_URL=http://backend:8000`).

## 烟测
```bash
python -m pytest tests/test_smoke.py      # streamlit AppTest 验证 app/五页可渲染, 不点真后端
```