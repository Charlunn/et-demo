# spark-pricing

[![CI](https://github.com/Charlunn/et-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/Charlunn/et-demo/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![license](https://img.shields.io/badge/license-MIT-green)

> 电力现货交易 **端到端可交付模块** demo: 负荷预测 → 分段报价 → 联合出清 (LP, 取对偶变量当 LMP) → 双结算三层 → 回测复盘, 外加一个**给电力交易员/分析师用的 Streamlit 产品工作台** (非 API 调试器). 整体可直接搬进对方系统.
>
> An end-to-end, drop-in module for power spot-market trading: load forecast → segmented bidding → joint clearing (LP, LMP from duals) → three-layer settlement → backtest, plus a **Streamlit product workbench for traders/analysts** (not an API debugger).

## 架构 / 业务主线 (SPEC §1 / PRD §1)

```
负荷预测/可再生能源出力
        │
        ▼
【日前报价】 分段报价曲线 (≤10 段, 边际成本 + 可选预测加成)
        ▼
【日前出清】 能量 + 1 个旋转备用 联合 LP  ─→ 节点 LMP(能量价/阻塞价/损耗价) 取自功率平衡对偶
        ▼
【双结算】 日前(计划×日前LMP) + 实时偏差((实际−计划)×实时LMP) + 中长期差价(CfD (合约价−参考价)×量)
        ▼
【回测/复盘】 策略1(报边际成本) vs 策略2(+预测加成) → BacktestReport (PnL/命中率/信息比率/MAPE/最大回撤)
        ▼
【工作台前端】 5 业务页: 行情看板 / 报价工作台 / 出清与计划 / 结算对账 / 回测复盘
```

分层包结构 (SPEC §2): `app/api/routes`(薄路由) → `app/services`(纯业务) → `app/domain`(纯领域/算法, 无 IO) → `app/models`+`app/repositories`+`app/db` (DB) ; `app/core` 横切 (config/logging/security/clock/errors).

## 快速上手 · 本地跑法 / Quickstart · local

```bash
# 0) 需要 Python 3.12 与 uv (§10 选型)
python --version   # 3.12
pip install uv      # 或参考 uv 官方安装

# 1) 装依赖
uv sync --extra dev

# 2) 建表 (默认 SQLite; 想用 Postgres 设 DATABASE_URL)
cp .env.example .env
uv run alembic upgrade head

# 3) 测试 + 覆盖门 + lint + 严格类型
uv run pytest --cov                          # 52 tests; cov-fail-under 80 (app/services+app/domain)
uv run ruff check app tests scripts && uv run ruff format --check app tests scripts
uv run mypy                                  # strict on app/core,app/domain,app/services

# 4) 跑主线产出报告
uv run python -m app.cli backtest --days 1 --line-limit 80 --model persistence
#   → 装订好的 JSON BacktestReport (96 时段, 策略2 胜基线, 中文/英文小结)

# 5) 起后端 + 前端
uv run python -m app.cli serve --port 8000            # 后端 :8000 ; /docs Swagger
# 另开一个终端:
cd frontend && uv venv --python 3.12 .venv
.venv\\Scripts\\activate  (Windows) 或 source .venv/bin/activate  (Unix)
uv pip install -r requirements.txt
streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
# 浏览器打开 http://localhost:8501 ; 登录 trader / trader-secret
```

## 快速上手 · Docker 跑法 / Quickstart · docker

```bash
docker compose up --build
#   前端 http://localhost:8501   (Streamlit 产品工作台)
#   后端 http://localhost:8000   (/healthz /readyz /docs)    默认凭据 trader / trader-secret
#   数据库 postgres:16 (compose 内置 db 服务, backend 启动时自动 alembic upgrade head)
```
本机已实测 `docker compose up --build` 真跑通 (非骨架):
- `GET /healthz` → 200 `{"status":"ok"}`
- `GET /readyz` → 200 `{"ready":true,"db":"ok"}`
- `GET /docs` → 200 (Swagger)
- `GET http://localhost:8501` → 200 (工作台页)
- `POST /token` 颁 JWT; `POST /backtest` (受 `scope:backtest:run` 保护) → 200 BacktestReport (策略2 胜基线).

## 域事实速查 (提词卡 · domain fact cheat-sheet)

> 演示前背记, 避免领域露馅 (PRD §2).

- **现货出清是 LP 优化, 取约束对偶当 LMP**, 不是"撮合配对" (撮合属中长期). demo 用 SCED 经济调度层 (固定组合), 取节点平衡对偶作 LMP; 阻塞价 = 负荷节点 LMP − 参考节点 LMP, 损耗 = 0 (生产才计).
- **LMP = 系统边际能量价 + 阻塞价 + 损耗价**, 按节点分解; 不混"统一出清".
- **双结算** = 日前(计划×日前LMP) + 实时偏差((实际−计划)×实时LMP), 避免双重计价; 实时偏差仅对偏差电量按实时价结算 (重新调度的范围是全网, 只对偏差电量计实时价).
- **中长期 = 金融差价合约 (CfD)**, 物理交付解耦, 按"合约价 − 省级现货参考价"结算; 三层收益 = 中长期差价 + 现货日前 + 现货偏差.
- **联合出清 = 能量 + 旋转备用**; 调频/AGC 通常是单独辅助服务市场, demo 明确略去 AGC.
- **日前粒度统一 15 分钟 × 96 段**; 实时简化同 15 分钟, 注释标生产为 5 分钟滚动.
- **集中式代表省份**: 广东/山西/山东/蒙西; **浙江是分散式**; 四川水电为主、争议大, 不列为集中式铁板.
- demo 硬事实: 5 台机组, 2 节点 (1 参考 / 1 负荷), 节点间线路有容量上限 → 制造真阻塞; 1 个 CfD 覆盖中长期层.

## 诚实声明 / Honesty statement

- **真跑**: Persistence 预测器 (默认, 零依赖); XGBoost 预测器 (若装 `uv sync --extra xgboost`, 装则真跑, 否则工厂回退 Persistence 且 log warn); 出清 LP (pulp + CBC); 三层结算; 回测指标.
- **stub / 不做**: LSTM (`lstm_stub.py` log warn, 返回 Persistence 结果, 绝不当真); 真实平台对接/真爬虫 (用固定 seed 合成行情, seed=20240101); UC 整数 (SCED 取 LP 对偶即真实 LMP, 详见 ADR 0001); 损耗 (设 0, 生产才计).
- 合成行情来源: `scripts/seed_demo.py` 固定 seed 复现; 不接任何真实市场.

## 文档中心
完整企业级文档见 [docs/README.md](docs/README.md):
- [使用手册 USER_GUIDE](docs/USER_GUIDE.md) (业务用户) · [接口文档 API](docs/API.md) · [架构 ARCHITECTURE](docs/ARCHITECTURE.md)
- [部署 DEPLOYMENT](docs/DEPLOYMENT.md) · [运维 OPERATIONS](docs/OPERATIONS.md) · [安全 SECURITY](SECURITY.md)

## ADR 索引
- [0001 · SCED LP 取对偶当 LMP, 不做 UC 整数](docs/adr/0001-sced-lp-cfd.md)
- [0002 · 预测器接口: Persistence 默认 + XGBoost 可选 + LSTM stub](docs/adr/0002-forecaster-interface.md)
- [0003 · 前端用 Streamlit 做产品工作台, 而非 API 调试器](docs/adr/0003-frontend-as-product.md)

## 安全说明
见 [SECURITY.md](SECURITY.md): secret fail-fast + gitleaks、JWT + scope、限流 + CORS allowlist(通配被拒)、全参数化 SQL、Clock 注入、ProblemDetail 不泄栈.

## API 概览 (SPEC §5)
| Method | Path | 鉴权 | 用途 |
|---|---|---|---|
| GET | /healthz · /readyz | none | 存活 / 就绪探针 |
| POST | /token | none (凭据) | 颁 access token |
| GET | /units | user | 机组清单 + 成本曲线参数 |
| GET | /market?node=&span= | user | 行情看板历史 LMP + 负荷 |
| POST | /bids | user | 用策略生成分段报价 (不让前端手填 JSON) |
| GET | /bids?unit_id= | user | 取机组待出清报价队列 |
| POST | /clearing | user | 跑日前联合出清 |
| POST | /settlement | user | 跑双结算三层 |
| POST | /forecast | user | 预测 LMP (可切模型) |
| POST | /backtest | scope:backtest:run | 跑回测 (受 scope 保护) |
| GET | /stream?node=&series=&span= | user | 实时 tick 模拟推流 + 1h 聚合 |

## 工程 (P2)
- 多阶段 Dockerfile + `docker-compose.yml` (backend+db+frontend 三服务, 本地真能跑).
- `.github/workflows/ci.yml`: ruff check/format-check + mypy(strict) + alembic upgrade head + pytest(--cov-fail-under 80) + gitleaks.
- `Makefile` 兼顾; 因 Windows 无 make, README 直接给 uv 命令 (零到运行).
- 前端烟测 `frontend/tests/test_smoke.py` 用 streamlit AppTest 验证 app + 五业务页可渲染 (不点真后端).

## 技术栈 (SPEC §10 已定)
Python 3.12 · uv (pyproject + uv.lock) · FastAPI · Pydantic v2 · SQLAlchemy 2.0 (async) · Alembic · pulp (LP, 取对偶 LMP) · structlog · jose(JWT) · slowapi · Streamlit + plotly + httpx · PostgreSQL 16 (docker) / SQLite (本地).