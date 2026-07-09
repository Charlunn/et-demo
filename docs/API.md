# 接口文档 · spark-pricing REST API

> 后端 FastAPI. 交互式文档 (Swagger UI) 运行时可访问 `http://<host>:8000/docs`, OpenAPI JSON 在 `/openapi.json`. 本文件是离线契约参考.

---

## 1. 通用约定

- **Base URL**: `http://<host>:8000` (反代后通常 `https://<domain>/api`)
- **内容类型**: 请求/响应均 `application/json` (除 `/token` 用表单)
- **鉴权**: OAuth2 Bearer JWT. 除 `/healthz` `/readyz` `/token` 外全部需 `Authorization: Bearer <token>`
- **请求 ID**: 每个响应带 `X-Request-ID` 头, 与日志、错误信封中的 `request_id` 一致, 便于排障
- **时间**: ISO 8601 UTC
- **粒度**: 时段为 15 分钟, 一日 96 段

---

## 2. 鉴权流程

### 2.1 获取令牌

```
POST /token
Content-Type: application/x-www-form-urlencoded

username=trader&password=trader-secret
```

响应 `200`:
```json
{ "access_token": "eyJhbGci...", "token_type": "bearer" }
```
失败 `401`: 见错误信封. 令牌含 `scopes` 声明, 有效期由 `ACCESS_TOKEN_EXPIRE_MINUTES` 控制 (默认 60 分钟).

### 2.2 使用令牌

```
GET /units
Authorization: Bearer eyJhbGci...
```

### 2.3 scope 保护

`/backtest` 需要 `backtest:run` scope. 令牌无该 scope → `403`.

---

## 3. 错误信封 (RFC 7807 ProblemDetail)

所有错误统一返回:
```json
{
  "type": "about:blank",
  "title": "Not found",
  "status": 404,
  "detail": "未找到机组: NOPE",
  "instance": "/bids",
  "request_id": "a1b2c3d4..."
}
```

| status | 触发 |
|---|---|
| 401 | 缺令牌 / 令牌无效或过期 |
| 403 | scope 不足 (越权) |
| 404 | 资源不存在 (如未知机组) |
| 422 | 请求体校验失败 (Pydantic) 或业务校验失败 |
| 429 | 触发限流 |
| 500 | 服务内部错误 (不回栈, 服务端记 full log) |

---

## 4. 端点

### 健康探针

| Method | Path | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/healthz` | 无 | 存活探针 → `{"status":"ok","app":"spark-pricing"}` |
| GET | `/readyz` | 无 | 就绪探针 (探 DB) → `{"ready":true,"db":"ok"}`; DB 不通 503 |

---

### GET /units — 机组清单

用于报价页列机组 + 成本曲线参数.

响应 `200` (数组):
```json
[{
  "unit_id": "G1", "node_id": "REF",
  "a": 0.02, "b": 20.0, "c": 0.0,
  "p_min": 0.0, "p_max": 120.0,
  "ramp_up": 60.0, "ramp_down": 60.0, "is_must_run": false
}]
```
字段: `a/b/c` 为二次成本 `C(P)=aP²+bP+c` 系数; 边际成本 `2aP+b`.

---

### GET /market — 行情看板

查询参数:
| 参数 | 类型 | 默认 | 约束 |
|---|---|---|---|
| `node` | string | (全部) | `REF` / `LOAD` |
| `span` | int | 96 | 1–288, 返回最近多少时段 |

响应 `200`:
```json
{
  "lmp":  [{"ts":"2024-01-01T00:00:00Z","node":"LOAD","value":48.3}],
  "load": [{"ts":"2024-01-01T00:00:00Z","node":"LOAD","value":150.2}],
  "blocked_periods": [5, 6, 7]
}
```
`blocked_periods` 为出现阻塞 (负荷节点 LMP 显著高于参考节点) 的时段序号.

---

### POST /bids — 生成分段报价

> 用策略生成报价, **不接受前端手填报价 JSON**.

请求体:
```json
{ "unit_id": "G1", "strategy": "marginal", "risk_markup": 5.0, "forecast_lmp": null, "periods": 96 }
```
| 字段 | 类型 | 约束 |
|---|---|---|
| `unit_id` | string | 1–32 字符, 须为已知机组 (否则 404) |
| `strategy` | string | `marginal` 或 `marginal_plus_forecast` |
| `risk_markup` | float | 0–500 (元/MWh) |
| `forecast_lmp` | float? | 0–2000, 策略2 的预测加成参考 |
| `periods` | int | 1–96 |

响应 `201`:
```json
{
  "unit_id": "G1", "period": 0, "strategy": "marginal",
  "segments": [{"price": 20.4, "mw": 12.0}],
  "segment_count": 10
}
```
分段 ≤ 10; 价格随边际成本单调非降.

### GET /bids?unit_id=G1 — 取待出清报价队列

响应 `200`: `BidCurve[]` (同上结构的数组).

---

### POST /clearing — 日前联合出清

请求体:
```json
{
  "periods": 96, "line_flow_limit_mw": 80.0,
  "days": 1, "use_seed": true,
  "load_ref": [100.0], "load_load": [150.0],
  "reserve_requirement_mw": null
}
```
| 字段 | 说明 |
|---|---|
| `periods` | 1–96 |
| `line_flow_limit_mw` | 线路潮流上限, 越小越易阻塞 |
| `use_seed` | true 用可复现合成负荷; false 用 `load_ref/load_load` (长度须 ≥ periods, 否则 422) |

响应 `200`:
```json
{
  "status": "optimal", "total_cost": 12345.6,
  "periods": [{
    "period": 0,
    "p": {"G1": 120.0, "G2": 30.0},
    "r": {"G1": 5.0},
    "lmp": {"REF": 28.0, "LOAD": 46.0},
    "lmp_components": {"LOAD": {"energy": 28.0, "congestion": 18.0, "loss": 0.0}},
    "line_flow_mw": 80.0, "blocked": true
  }]
}
```
`lmp` 取自节点功率平衡约束对偶变量; 阻塞价 = 负荷节点 LMP − 参考节点 LMP; 损耗恒 0 (注释: 生产才计). 无可行解 → `422 Clearing infeasible`.

---

### POST /settlement — 双结算三层

请求体:
```json
{
  "s_da": 100.0, "s_act": 110.0, "lmp_da": 300.0, "lmp_rt": 350.0,
  "cfd": {"strike_price": 280.0, "quantity": 50.0, "reference_px": 300.0}
}
```
响应 `200`:
```json
{ "da": 30000.0, "deviation": 3500.0, "cfd": -1000.0, "total": 32500.0,
  "manual_check_note": "DA=S_da*LMP_da; DEV=(S_act-S_da)*LMP_rt; CFD=(P_c-LMP_ref)*Q_c" }
```
`cfd` 可省 (为 null 则该层为 0).

---

### POST /forecast — LMP 预测

请求体:
```json
{ "horizon": 96, "model_name": "persistence", "seed_days": 2, "target_node": "LOAD" }
```
`model_name`: `persistence` (默认真跑) / `xgboost` (装则真跑, 缺则回退 persistence 并 log warn) / `lstm` (stub, 返回 persistence).

响应 `200`:
```json
{ "values": [45.3, 38.4, ...], "model_name": "persistence",
  "honesty": "Persistence/XGBoost 真跑; LSTM 仅 stub" }
```

---

### POST /backtest — 回测 (受 scope 保护)

> 需 `backtest:run` scope, 否则 403. 限流 5/分钟.

请求体:
```json
{ "days": 1, "line_flow_limit_mw": 80.0, "model": "persistence",
  "load_node": "LOAD", "cfd_strike": 300.0, "cfd_quantity": 1000.0 }
```
响应 `200`:
```json
{
  "periods": 96, "beats_baseline": true,
  "strategy_baseline": {"name":"marginal","model_name":"n/a","metrics":{...}},
  "strategy_forecast": {"name":"marginal_plus_forecast","model_name":"persistence","metrics":{
    "net_pnl": 657197.1, "hit_rate": 0.55, "profit_factor": 1.3,
    "information_ratio": 0.12, "clearing_mape": 33.6, "max_drawdown": 18.0
  }},
  "pnl_curve_baseline": [...], "pnl_curve_forecast": [...],
  "summary_zh": "...", "summary_en": "..."
}
```

---

### GET /stream — 实时 tick 模拟推流

查询参数: `node` (LOAD/REF), `series` (lmp/load), `span` (1–288), `aggregate_1h` (bool, 1h 聚合).

响应 `200`:
```json
[{"ts":"2024-01-01T00:00:00Z","node_id":"LOAD","series_type":"lmp","value":40.0,"quality_flag":"OK"}]
```
生产为 5 分钟滚动, demo 简化为 15 分钟 (注释说明).

---

## 5. 限流

| 端点 | 限额 |
|---|---|
| `/bids` | 10 / 分钟 |
| `/clearing` | 10 / 分钟 |
| `/forecast` | 20 / 分钟 |
| `/backtest` | 5 / 分钟 |

超限 → `429`. 按客户端 IP 计数 (slowapi).

---

## 6. curl 速查

```bash
# 登录拿 token
TOK=$(curl -s -X POST http://localhost:8000/token \
  -d "username=trader&password=trader-secret" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 机组
curl -s http://localhost:8000/units -H "Authorization: Bearer $TOK"

# 出清
curl -s -X POST http://localhost:8000/clearing -H "Authorization: Bearer $TOK" \
  -H "Content-Type: application/json" \
  -d '{"periods":96,"line_flow_limit_mw":80,"days":1,"use_seed":true,"load_ref":[100],"load_load":[150]}'

# 回测 (需 scope)
curl -s -X POST http://localhost:8000/backtest -H "Authorization: Bearer $TOK" \
  -H "Content-Type: application/json" -d '{"days":1,"model":"persistence"}'
```