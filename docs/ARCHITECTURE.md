# 架构文档 · spark-pricing

> 面向工程师 / 集成方. 分层设计、数据流、模块职责、关键取舍. 与 SPEC §2/§3 一致.

---

## 1. 分层总览

```
┌──────────────────────────────────────────────────────────────┐
│ frontend/  Streamlit 产品工作台 (5 业务页)                     │
│   pages/*.py ── api_client.py(唯一后端通道 httpx) ──▶ 后端 REST │
└──────────────────────────────────────────────────────────────┘
                              │ HTTP + JWT
┌──────────────────────────────────────────────────────────────┐
│ app/api/routes/   薄路由: 解析 → 调 service → 装响应           │
│   (不导 SQLAlchemy, 不写业务逻辑)                              │
├──────────────────────────────────────────────────────────────┤
│ app/services/     业务编排: 纯函数/薄服务 (不导 FastAPI 类型)   │
├──────────────────────────────────────────────────────────────┤
│ app/domain/       纯领域 + 算法 (无 IO, 最易测)                │
│   units / clearing_engine(LP) / settlement / forecaster/ / metrics │
├──────────────────────────────────────────────────────────────┤
│ app/repositories/ DB 访问唯一去处   app/models/  SQLAlchemy ORM │
│ app/db/           engine/session/timeseries                    │
├──────────────────────────────────────────────────────────────┤
│ app/core/         横切: config / logging / security / clock / errors / ratelimit │
└──────────────────────────────────────────────────────────────┘
                              │
                     PostgreSQL 16 / SQLite (本地)
```

**依赖方向单向向下**, 由 `tests/test_layers.py` 静态守护:
- `api/**` 不导 `sqlalchemy` / `app.models`
- `services/**` 不导 `fastapi`
- `domain/**` 不导 `fastapi` / `sqlalchemy` / `httpx`

---

## 2. 业务主线数据流 (SPEC §1)

```
seed_demo(固定seed) ─┐
                     ▼
   负荷预测 ── forecaster(Persistence/XGBoost) ──▶ LMP 预测序列
                     │
   报价 ── services/bidding ──▶ 分段报价曲线 (≤10段, 边际成本[+预测加成])
                     │
   出清 ── domain/clearing_engine (pulp LP) ──▶ 节点LMP(对偶) + 机组P/R + 阻塞
                     │
   结算 ── domain/settlement ──▶ 日前 + 实时偏差 + 中长期差价(CfD)
                     │
   回测 ── services/backtest + domain/metrics ──▶ BacktestReport (6指标+中英小结)
```

---

## 3. 关键模块职责

| 模块 | 职责 | 关键点 |
|---|---|---|
| `domain/clearing_engine.py` | 日前联合出清 LP | pulp 建模, 节点功率平衡约束**对偶变量即 LMP**; 线路潮流约束制造阻塞; 求解后按约束名取 `.pi` |
| `domain/settlement.py` | 三层结算纯函数 | 日前/实时偏差/CfD; 避免双重计价 |
| `domain/forecaster/` | 预测器 ABC + 3 实现 | Persistence 默认真跑; XGBoost 可选; LSTM stub; 工厂缺依赖优雅回退 |
| `domain/metrics.py` | 回测指标纯函数 | 6 指标, 全程除零保护 |
| `services/backtest.py` | 回测编排 | 跑两策略 → 出清 → 结算 → 指标 → 报告 |
| `core/config.py` | 集中配置 | Pydantic BaseSettings, 业务零裸数字; SECRET_KEY fail-fast |
| `core/security.py` | JWT + scope | HS256, `get_current_user`, `require_scope` |
| `db/timeseries.py` | 时序窄表 | dialect-aware 1h 聚合 view (PG date_trunc / SQLite strftime); retention 配置 stub |

---

## 4. 技术选型 (SPEC §10 已定)

| 关注点 | 选型 | 理由 |
|---|---|---|
| 包管理 | uv (pyproject + uv.lock) | 锁定可复现, CI 从零可装 |
| LP 求解 | pulp + CBC | 纯 Python 装得稳, 对偶可读 |
| Web | FastAPI + Pydantic v2 | 类型+校验+OpenAPI 一体 |
| ORM/迁移 | SQLAlchemy 2.0 async + Alembic | 参数化查询, 迁移可控, 不用 create_all |
| 前端 | Streamlit | 企业感卡片/图表, 1h 可交付产品工作台 (见 ADR 0003) |
| DB | PostgreSQL 16 / SQLite | 生产 PG, 本地/测试 SQLite |

---

## 5. 横切关注点

- **配置**: 全部业务门限从 env 读, 集中 `core/config.py`; SECRET_KEY 生产 fail-fast.
- **日志**: structlog 结构化; `LoggingMiddleware` 注 request_id, 记 method/path/status/duration_ms.
- **错误**: 领域异常 → 全局 handler → RFC7807 ProblemDetail (不泄栈).
- **安全**: JWT + scope + 限流 (slowapi) + CORS allowlist + 全参数化 SQL + Clock 可注入.
- **可测**: domain 纯函数最易测; 出清/结算有手算对照; 覆盖门 ≥80% (实测 89.9%).

---

## 6. 决策记录 (ADR)
- [0001 · SCED LP 取对偶当 LMP, 不做 UC 整数](adr/0001-sced-lp-cfd.md)
- [0002 · 预测器接口: Persistence/XGBoost/LSTM stub](adr/0002-forecaster-interface.md)
- [0003 · 前端用 Streamlit 做产品工作台](adr/0003-frontend-as-product.md)

---

## 7. 已知边界 (诚实标注, SPEC §4 out-of-scope)
- 只做 SCED 经济调度层 (LP), 不做 UC 整数 (SCUC).
- 损耗分项设 0 (阻塞是重点).
- LSTM 为 stub; 无真实平台对接 / 真爬虫 (固定 seed 合成行情).
- 报价待出清队列当前为进程内 (repositories 已备好持久化路径, 多副本前需迁 DB).