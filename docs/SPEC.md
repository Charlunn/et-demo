# SPEC · 电力现货交易 Demo（1 小时可交付的企业级精品）

> 配套 `PRD.md`。本文定义**到底建什么、叫什么、什么映射什么**。读完这份应当可以直接照着落代码。
> 与 CLAUDE.md 一致：最小可验、无 speculative、外科手术式。
> 不执行——执行前叫你。

---

## 1. 项目身份

- **名称**:`spark-pricing`(暂定；可改)——意为"报价/出清/复盘"意义上的 spark。
- **形态**: 一个 Python 包 `app/`(FastAPI 后端 + 纯函数核心) + 一个 `frontend/` Streamlit 产品工作台 + `tests/` + 工程化配套。**整体构成一个可直接搬进对方系统的完整模块**, 不是一堆 API。
- **Python**: 3.12(单一版本，CI 矩阵不发散，省时)。
- **包管理**: `pyproject.toml` + `uv.lock`(若用 uv)或 `requirements*.txt`(锁)。**二选一，不混**。

---

## 2. 目录结构（A 层骨架,一眼看懂是规整企业项目）

```
demo/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 实例装配(app, 中间件, exception handlers, 路由挂载, startup/shutdown log)
│   ├── api/
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py        # /healthz /readyz
│   │       ├── bids.py          # 提交报价 / 拿报价曲线
│   │       ├── clearing.py      # 触发出清 / 拿出清结果(计划+LMP)
│   │       ├── settlement.py    # 跑双结算
│   │       ├── backtest.py      # 跑回测 / 拿 BacktestReport
│   │       ├── forecast.py     # LMP 预测(可切模型名)
│   │       └── stream.py        # 实时 tick 模拟推流
│   ├── services/                # 纯业务逻辑, 不导 FastAPI 类型, 不直接建 session
│   │   ├── bidding.py
│   │   ├── clearing.py          # 调 domain/clearing 解 LP
│   │   ├── settlement.py
│   │   ├── backtest.py
│   │   ├── forecast.py          # 选 Forecaster
│   │   └── stream.py
│   ├── domain/                  # 纯领域对象+算法, 无 IO, 最易测
│   │   ├── units.py             # 机组成本曲线 aP²+bP+c, 爬坡/min-output
│   │   ├── clearing_engine.py   # LP 出清(PuLP/cvxpy 或 scipy.optimize.linprog)
│   │   ├── settlement.py        # 三层结算公式（纯函数）
│   │   ├── forecaster/
│   │   │   ├── base.py          # Forecaster ABC: forecast(history,horizon)->np.ndarray ; name
│   │   │   ├── persistence.py   # 默认, 零依赖, 实跑
│   │   │   ├── xgboost_impl.py  # 可选, import 时缺失则工厂回退见下
│   │   │   └── lstm_stub.py     # stub, __init__ log warn, 返回 persistence
│   │   └── metrics.py            # PnL/命中率/信息比率/MAPE/最大回撤（纯函数）
│   ├── models/                  # SQLAlchemy 2.0 ORM
│   │   ├── base.py              # Base + created_at/updated_at mixin
│   │   ├── price_tick.py
│   │   ├── bid.py
│   │   ├── clearing_result.py
│   │   └── contract.py          # CfD
│   ├── schemas/                 # Pydantic v2 请求/响应（带 Field 约束 + examples）
│   │   ├── bid.py
│   │   ├── clearing.py
│   │   ├── settlement.py
│   │   ├── backtest.py
│   │   └── errors.py            # ProblemDetail (RFC7807)
│   ├── repositories/            # DB 访问唯一去处
│   │   ├── price_tick.py
│   │   ├── bid.py
│   │   └── clearing_result.py
│   ├── core/
│   │   ├── config.py            # Settings(BaseSettings), fail-fast SECRET_KEY
│   │   ├── logging.py           # structlog/JSON + request_id 中间件
│   │   ├── security.py          # JWT 解析/校验 + require_scope Depends
│   │   ├── clock.py             # Clock time provider via Depends
│   │   └── errors.py            # 领域异常基类 + 映射器
│   └── db/
│       ├── session.py           # async engine + get_db AsyncSession yield
│       └── timeseries.py        # Timescale 模拟: 窄表/索引/time_bucket 等价聚合 view/retention 配置
├── alembic/
│   ├── env.py                   # target_metadata = Base.metadata
│   ├── script.py.mako
│   └── versions/0001_init.py    # baseline
├── tests/
│   ├── conftest.py              # client fixture, rollback-session fixture, frozen clock
│   ├── test_clearing.py         # LMP 由 LP 对偶（对给定算例手算对照）
│   ├── test_settlement.py       # 三层结算手算对照
│   ├── test_bidding.py
│   ├── test_forecast.py         # Persistence 实跑; XGBoost 缺则跳(factory 兜底)
│   ├── test_backtest.py         # 跑出 BacktestReport, 字段非空, 策略胜基线
│   ├── test_api_*.py            # happy/422/401/404 + ProblemDetail 形状
│   ├── test_security.py         # 未授权→401, 越权→403
│   └── test_layers.py           # import-linter 等价: 路由不导 SA, service 不导 FastAPI 类型
├── scripts/
│   └── seed_demo.py             # 生成可复现的合成行情(负荷+LMP历史+机组参数), 固定 seed
├── docs/
│   ├── PRD.md  SPEC.md
│   └── adr/
│       ├── 0001-sced-lp-cfd.md  # 为何用 LP SCED(固定组合)取对偶当 LMP; 为何不做 UC 整数
│       │   └── 0002-forecaster-interface.md  # 为何 LSTM stub、Persistence 默认、XGBoost 可选
│       │   └── 0003-frontend-as-product.md  # 为何用 Streamlit 做产品工作台而非API调试器; 品牌与克制原则
├── demo-data/                   # 生成的合成数据落盘(csv/parquet 小份), 让回测可复现
├── frontend/                     # Streamlit 产品工作台(见 PRD §2.1; 不是 API 调试器)
│   ├── app.py                    # 入口: 多页导航 + 全局主题/布局 + 会话态(登录、当前选中机组/节点/区间)
│   ├── api_client.py            # 对后端 REST 的薄封装(httpx); 页面不直接拼 URL
│   ├── pages/
│   │   ├── 1_行情看板.py          # 多节点 LMP 折线 + 实时滚动 tick(模拟)+ 负荷分布 + 阻塞标记 + 导出
│   │   ├── 2_报价工作台.py        # 机组 + 分段报价表(≤10段) + 策略/风险加成参数 + 实时重算 + 提交报价
│   │   ├── 3_出清与计划.py        # 运行出清 → 每节点 LMP(能量/阻塞/损耗) + 每机组 P/R + 阻塞可视化 + 时段下钻
│   │   ├── 4_结算对账.py          # 三层收支明细(日前/实时偏差/中长期差价) + 合计 + 一致性标注 + 生成结算单
│   │   └── 5_回测复盘.py          # 两策略 PnL 曲线对照 + 指标表 + 中文小结 + 导出复盘报告
│   ├── components/               # 跨页复用小组件(KPI 卡/图表包装/空载错态) — 仅确有复用时才建
│   ├── theme.py                  # 品牌色/排版常量(单主色 + 2 中性辅色); 所有页引用
│   ├── requirements.txt          # streamlit + pandas + plotly + httpx
│   └── README.md                 # 明示: 电力交易工作台产品, 非API调试器; 本地/容器两跑法
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile                   # 多阶段 builder→slim
├── docker-compose.yml           # backend + db(postgres) + frontend(streamlit) 三服务; 本地 `docker compose up` 必须真起来
├── Makefile
├── pyproject.toml
├── requirements.txt / requirements-dev.txt
├── README.md  SECURITY.md  CONTRIBUTING.md
└── CLAUDE.md (已有)
```

---

## 3. 核心算法规范（domain 层，必须真实且可测）

### 3.1 机组成本与报价曲线（services/bidding → domain/units）

- 机组参数: `a, b, c`（二次成本 `C(P)=aP²+bP+c`），`P_min, P_max`, `ramp_up, ramp_down`, `is_must_run`(可再生)。
- 分段报价: 给定机组，将 `[P_min,P_max]` 切 ≤10 段，每段价 = 边际成本 `dC/dP=2aP+b`（+ 可选风险加成 `risk_markup`，来自 `settings`）。
- 输出: 每机组每时段一组 `(price, mw)`。
- 策略 1（基线）"报边际成本": margin-cost 报价。
- 策略 2（待测）"边际成本+预测价加成": 用 §3.4 的 LMP 预测调整每段报价的阶梯。

### 3.2 日前出清（domain/clearing_engine）—— demo 的硬核可信度所在

- **模型**: 能量 + 1 个旋转备用，联合出清的 LP。
- 决策变量: `P[g,t]` 各机组各时段出力；`R[g,t]` 各机组各时段旋转备用。
- 目标: min Σ C_g(P[g,t])（用边际成本近似即可，LP 下足够；注明 UC/整数态略去）。
- 约束:
  - 功率平衡: Σ_g P[g,t] = Load[t]（负荷价格无弹性，固定预测值）。
  - 备用平衡: Σ_g R[g,t] >= ReserveReq[t]。
  - 机组: P_min<=P<=P_max；P[g,t]+R[g,t]<=P_max；ramp: |P[g,t]-P[g,t-1]|<=ramp。
  - 网络: 2 节点，线路潮流 `F=Σ(节点注入)` 受 `|F|<=F_max` 限（**这制造阻塞，LMP 分解才示得出**）。
- **LMP 取法**: 求解后读**功率平衡约束的对偶变量**(影子价)作为节点 LMP；阻塞价 = 负荷节点LMP − 参考节点LMP；损耗 = 0（注释说明生产才计）。
- 求解器: 优先 `pulp`(纯 Python，装得稳)；或 `scipy.optimize.linprog`。1h 内若装 cvxpy 不顺则立即降级 pulp/linprog，**不让依赖拖垮**。
- 输出: 每节点每时段 `LMP{energy,congestion,loss}` + 每机组 `P, R` + 是否阻塞标记。

### 3.3 双结算（domain/settlement，纯函数）

输入: 日前计划电量 `S_da`、实际电量 `S_act`、日前 LMP `LMP_da`、实时 LMP `LMP_rt`、CfD `(合约价P_c, 合约量Q_c, 参考价LMP_ref)`。
- 日前结算 = `S_da × LMP_da`
- 实时偏差结算 = `(S_act − S_da) × LMP_rt`
- 中长期差价 = `(P_c − LMP_ref) × Q_c`
- 三层收益 = 上述三者之和（对发电侧；按需给符号方向）
- 输出: `SettlementBreakdown{da, deviation, cfd, total}`，每个子项带金额与单位，纯函数易做对照测试。

### 3.4 价格预测（domain/forecaster，接口即 demo 的主要交付物）

- ABC: `Forecaster.forecast(history: np.ndarray, horizon: int) -> np.ndarray`，`name: str`。
- 默认 `PersistenceForecaster`(零依赖，实跑，price_{t+1}=price_t + 日周期项)。
- `XGBoostForecaster`: 可选依赖，import 失败 → 工厂 fallback 到 Persistence 并 log warn。
- `LSTMForecaster`: stub，`__init__` log warn "stub: returns persistence; real LSTM needs GPU/large data"，返回 persistence。
- 工厂按 `settings.DEFAULT_FORECASTER` 或请求参数 `model_name` 选，**缺则优雅回退**。
- 评估: 在同一测试窗对 Persistence vs XGBoost(若装) 报 MAE/MAPE; **绝不把 LSTM 标成真结果**。
- 回测跑同测试窗，让 XGBoost 显示对 Persistence 的小幅胜出（哪怕微小），以示"真 ML"。

### 3.5 回测/复盘（domain/metrics + services/backtest）

- 重放合成历史: 跑策略 1(基线) vs 策略 2(加成)，各产报价 → 走出清 → 走结算 → 累计 PnL。
- 指标(`metrics.py` 纯函数):
  - 总收益 Net PnL
  - 命中率 Hit Rate
  - 盈亏比 Profit Factor
  - 信息比率（per-trade Sharpe）: mean(hourly PnL)/std×√8760
  - 出清价 MAPE / MAE
  - 最大回撤 Max Drawdown
- 输出 `BacktestReport`(Pydantic)，含两策略对照表 + 指标 + 一段(中文+英文)自然语言小结。
- **诚实验证**: LSTM 标 stub，Persistence/XGBoost 出真数。

### 3.6 实时数据处理模拟（services/stream + db/timeseries）

- 模拟推流: 用合成数据按 15-min(注释:生产 5-min) 产 `{ts, node_id, series_type, value}` 写入窄表。
- 窄表: `(id, ts TIMESTAMPTZ, node_id, series_type, value, quality_flag)`，**索引 (node_id, ts DESC)**。
- 聚合: 一个 view `price_1h` (`SELECT … GROUP BY time_bucket('1h',ts), node_id, avg …`)，SQLite 无 `time_bucket` 时用 `strftime` 等价实现，并注释。
- 保留策略: retention 配置对象 `{raw:'30d', rollup_1h:'1y'}` + 注释 stub job `drop_chunks`，说明生产才 `create_hypertable`。
- 批量写: bulk insert，带 `ingested_at`，支持 `ON CONFLICT (node_id,ts) DO UPDATE`（Postgres；SQLite 用 INSERT OR REPLACE）幂等重灌。
- 写一个量: 在 `/healthz` 或启动日志里打印"已灌 X rows/sec"以示实时面（注释说明合成来源）。

### 3.7 前端产品工作台（frontend/，Streamlit）—— 这次成败的关键判准

> **硬判准（作者与执行 agent 都须背记）**：这是给**电力交易员/分析师**用的产品工作台，**不是给开发者用的 API 调试器**。若任何页面上出现"贴一段 JSON body / 点 Send / 看返回 status 与 response 体"的手感，即视为整体失败——再漂亮的代码也救不回来。每个页面都是**业务动作的闭环**：选业务对象 → 看业务含义的可视化 → 改业务参数 → 看业务结果。

#### 3.7.1 布局与全局态
- 单入口 `frontend/app.py`: Streamlit 多页(`pages/1_…py` 自动生成侧边导航)。顶部放应用名 + 当前登录用户只读徽标 + 数据"合成/已同步"状态徽标。
- 全局会话态(st.session_state)：登录态(token)、当前选中节点、当前选中机组、当前回测区间。页面之间靠它连贯，不靠 URL 手传。
- `api_client.py`: 全部后端调用唯一通道(httpx)，含 base_url 从 env、超时、错误向上抛成业务文案；**页面里禁止出现裸 URL、禁止出现 `requests.post`**。
- `theme.py` + `.streamlit/config.toml`: 单一品牌主色(电力蓝/青绿二选一)、2 个中性辅色、浅色背景、深色文字、卡片化；**禁止花哨发光/玻璃拟态/渐变彩虹**。
- 每页必须显式写出：**这是谁的页面 / 他来做什么 / 操作完看到什么**（对应 PRD §2.1 表）。

#### 3.7.2 五个业务页一页一规范
- **1 行情看板**: 默认三列 KPI(均价/最高价/最低价侠自选中节点区间) + 多节点 LMP 折线(plotly, 5 色以内) + 模拟实时 tick 滚动表(可暂停) + 负荷日内分布柱状 + 节点阻塞高亮(红边)。可按节点/区间筛选、导出本段行情 csv。**禁止**: 任何"返回原始 JSON"。
- **2 报价工作台**: 左侧选机组 → 显示其成本曲线小图(边际成本线)；右侧分段报价表(行=96 时段或可折叠为代表性时段, 列=每段价/量, ≤10 段)；上方策略选择(报边际成本 / 边际成本+预测加成)+风险加成滑杆；改任一参数 → 表实时重算(防抖)；点"提交报价" → 写入待出清队列(后端存)。**禁止**: 让用户手填 JSON。
- **3 出清与计划**: 点"运行出清" → 进度 → 出结果:每节点 LMP 卡片(拆能量价/阻塞价/损耗价)+每机组出力与旋转备用表 + 阻塞可视化(2 节点拓扑小图,限流线标红)+时段下钻(点某时段看该时段机组排序)。**禁止**: 只甩一坨调度结果 JSON。
- **4 结算对账**: 给入实际电表数/选中长期合约 → 三层明细表(日前结算 / 实时偏差 / 中长期差价,各带金额与正负说明)+合计大数 + "与手算口径一致"绿勾标注 + "生成结算单"导出。**禁止**: 只显示一个 total。
- **5 回测复盘**: 选历史区间 + 选两条策略 → 运行 → 双 PnL 累计曲线对照 + 指标 6 项对照表(总收益/命中率/盈亏比/信息比率/出清价MAPE/最大回撤)+一段中文自然语言小结(程序生成,诚实标注哪些模型真跑哪些 stub)+"导出复盘报告"。**禁止**: 让用户去 JSON 里找指标。

#### 3.7.3 视觉与交互底线(企业且不老气)
- 留白多、边线细、轻投影; 一屏一个主任务; 不堆面饼。卡片区按业务分组(用 `st.container(border=True)`)。
- 数字用等宽对齐; 单位标注在表头/轴; 图表网格线细且半透明。
- 加载→骨架或 spinner + 文案; 空态有说明; 出错有业务化文案而非堆栈; 提交按钮在必填未満足时禁用。
- 图表 hover tooltip 只显必要 2–3 项, 不全量铺。

#### 3.7.4 防飘纪律(CLAUDE.md 在前端上的体现)
- 不做用不到的小部件; `components/` 只放确有跨页复用的小件, 单页一次性代码就地写。
- 不为"好看"加与业务无关的动画/装饰图。
- 前端不内置领域公式计算; 一切数值来自后端 API(单源真理), 前端只做呈现与参数收集——这样"工作台搬进对方系统"才成立。

#### 3.7.5 前端可测/可起
- `frontend/requirements.txt` 固定版本; `docker-compose` 的 `frontend` 服务以 `streamlit run app.py --server.port 8501 --browser.gatherUsageStats false` 起来, 与 backend 同网络, 通过服务名 `backend` 访问 API。
- 一支最小烟测: `frontend/tests/test_smoke.py` 用 streamlit AppTest 验证 `app.py` 可渲染、侧边导航含五个业务页名(不点真后端)。
- **Docker 必须真能跑**:执行阶段要本地 `docker compose up --build` 后确认 `localhost:8501` 出页面、`localhost:8000/healthz` 200、`localhost:8000/docs` 可达。

---

## 4. 安全 & 可观测规范（B 层，须留测试与痕迹）

### 4.1 配置与密钥（core/config.py）
- `Settings(BaseSettings)`：`database_url, secret_key, access_token_expire_minutes, debug, cors_origins: list[str], default_forecaster, risk_markup, reserve_requirement_mw, line_flow_limit_mw, retention_raw_days`。
- **SECRET_KEY fail-fast**: `model_validator` 若 `debug is False` 且 key==default 或 len<32 → `raise`，并有专门断言测试。
- `.env.example` 提交占位值；`.env` 在 .gitignore。

### 4.2 Auth（core/security.py）
- `OAuth2PasswordBearer` + JWT(HS256)；`get_current_user` Depends；`require_scope("backtest:run")` 写 endpoint。
- 至少一个写/敏感 endpoint（如 `POST /backtest`）受保护；其余读 endpoint 也走 `Depends(get_current_user)`。
- 测试: 无 token→401；scope 不足→403。

### 4.3 错误信封（core/errors.py + schemas/errors.py + main.py）
- 领域异常: `NotFoundError, ValidationError(Business), ClearingInfeasibleError`。
- 全局 handler 将 `HTTPException`、`RequestValidationError`、领域异常、兜底 `Exception` 全映射为 RFC7807 ProblemDetail `{type,title,status,detail,instance,request_id}`；兜底绝不回栈，服务端 log full。
- 测试断言某已知业务错误 → 期望 status + body 形状。

### 4.4 日志 & 中间件
- `core/logging.py`: structlog JSON（prod）或 pretty（dev via settings）；`LoggingMiddleware` 注 `request_id`，记 method/path/status/duration_ms。
- 业务代码无 `print()`；CI ruff 规则可加 T201（打印）告警（可选）。

### 4.5 限流 / CORS
- `slowapi` 挂在 auth/写 endpoint；CORS `allow_origins=settings.cors_origins`（prod 默认空列表，测试断言通配被拒）。

### 4.6 DB / 迁移 / 事务
- 异步 `async_engine` + `AsyncSession`；`get_db` yield 且异常时 rollback。
- Alembic `env.py` 拿 `Base.metadata` + `settings.database_url`；baseline revision；CI `alembic upgrade head`；**禁止 `create_all` 在 prod 路径**（测试可临时库用，但走 fixtures，不暴露给 prod）。
- 全参数化查询；无 f-string SQL。

### 4.7 时钟（core/clock.py）
- `Clock` 默认 `datetime.now(timezone.utc)`；经 `Depends` 注入；测试冻结。

---

## 5. API 契约（每个 endpoint 都映射到 §PRD-1 主线）

| Method | Path | 鉴权 | 请求体 | 响应 | 备注 |
|---|---|---|---|---|---|
| GET | /healthz | none | – | `{status}` | 存活 |
| GET | /readyz | none | – | `{db: ok, …}` | 依赖探测 |
| GET | /market?node=&from=&to= | user | – | `MarketView{lmp[],load[],blocked?}` | 行情看板拉历史/聚合 |
| GET | /units | user | – | `Unit[]` | 报价页列机组+成本曲线参数 |
| POST | /bids | user | `BidSubmit{unit_id, strategy, risk_markup}` | `BidCurve` | 用策略生成分段报价(**不让前端手填JSON**) |
| GET | /bids?unit_id= | user | – | `BidCurve[]` | 取该机组待出清报价队列 |
| POST | /clearing | user | `ClearingRequest` | `ClearingResult{schedule,P,R,lmp{energy,congestion,loss},blocked}` | 跑日前出清 |
| POST | /settlement | user | `SettlementRequest` | `SettlementBreakdown{da,deviation,cfd,total}` | 跑双结算 |
| POST | /forecast | user | `ForecastRequest{model_name?}` | `Forecast{values,model_name}` | 预测 LMP |
| POST | /backtest | scope:backtest:run | `BacktestRequest` | `BacktestReport` | 受 scope 保护; 回测页用 |
| GET | /stream?node=&series=&from=&to= | user | – | `PriceTick[]` | 实时面 + 1h 聚合 |

- 所有 request/response 皆 Pydantic v2，带 `Field(...)` 约束与 `examples`；每路由声明 `response_model`、`status_code`、`responses`、`tags`、`summary`。
- OpenAPI: `title/version/description` 填好；可 commit `openapi.json` 快照。

---

## 6. 测试矩阵（可独立验,CI 必跑）

- `test_clearing.py`: parametrized 给定算例 → LMP 与手算 LP 对偶一致(含一例制造阻塞看 congestion>0)。
- `test_settlement.py`: 给定 (S_da,S_act,LMP_da,LMP_rt,CfD) → 三层与手算一致。
- `test_bidding.py`: 分段报价段数 ≤10、价格随边际成本单调、≥0。
- `test_forecast.py`: Persistence 实跑返回 horizon 长数组；XGBoost 缺包装时工厂回退且 log warn(用 caplog)。
- `test_backtest.py`: `run_backtest(...)` 返回 BacktestReport，字段非空，策略 2 PnL 与基线均有限；指标常数为 0 的情况有保护(避免除零)。
- `test_api_*.py`: happy / 422 / 401 / 404 各至少 1 例；ProblemDetail 形状测试。
- `test_security.py`: 无 token→401；scope 不足→403；SECRET_KEY 默认值+prod → 启动 fail。
- `test_layers.py`: 等价 import-linter——静态断言 `app/api/**` 无 `from app.models`/`sqlalchemy`；`app/services/**` 无 `fastapi`。
- `frontend/tests/test_smoke.py`: streamlit AppTest 验证 `app.py` 可渲染、侧边导航含五个业务页名；**不点真后端**。
- coverage: `--cov-fail-under 80`（针对 app/services + app/domain；coverage 配置聚焦测试价值层，不强求路由胶水 100%）。
- `mark.seeded` 走复现合成数据(seed 固定)。
- **集成烟测(本地)**: `docker compose up --build` 后断言 `localhost:8501` 返回页面、`localhost:8000/healthz` 200、`localhost:8000/docs` 200。

---

## 7. 实施顺序 + 1h 裁剪优先级表（防超时）

> 严格按表执行；时间到就停在已完成的最高优先级，**剩余项留骨架文件 + commit 说明**。绝不因追求齐全而让主线跑不起来。

| 优先级 | 任务 | 时长 | verify | 超时则 |
|---|---|---|---|---|
| P0 | §2 骨架包目录 + pyproject + .env.example + Settings fail-fast + core/logging + main 装配 + /healthz | 10min | `make run` 起 + curl /healthz 200 | 无 web 也得有包可 import |
| P0 | domain/units + clearing_engine(LP, 取对偶) + 对一例测试 LMP 手算对照 | 15min | `make test test_clearing` 绿 | 退到 scipy.linprog |
| P0 | domain/settlement + 手算对照测试 | 5min | test_settlement 绿 | – |
| P0 | domain/forecaster(Persistence 默认 + 工厂回退) + services/backtest + metrics + 一条复现 seed | 12min | test_backtest 出报告 | XGBoost/lstm 一律 stub |
| P0 | 一条 CLI 把整条主线串起来跑出 BacktestReport | 5min | `python -m app.cli backtest` 出报告 | 退成 CLI 脚本 |
| P1 | api routes(bids/clearing/settlement/forecast/backtest/行情行情/结算对账流支撑端点)+ schema + ProblemDetail handler + auth(JWT) + 限流 | 18min | test_api/happy/422/401 绿 | 限流可后补 |
| P1 | frontend/ Streamlit 五业务页 + api_client + theme + 烟测; 页面对应业务闭环, **非 API 调试器** | 22min | `frontend/tests/test_smoke.py` 绿 + 浏览器肉眼过五个页 | 单页糙一点也算, 先五页骨架可见 |
| P1 | models + Alembic baseline + repositories + get_db + 实时窄表 + view | – | `alembic upgrade head` 绿 | 暂用内存/SQLite，文件保留迁移骨架 |
| P2 | Dockerfile + docker-compose(backend+db+frontend 三服务) + 本地 `docker compose up` **真跑通** | 超时外 | 8501 出页面 / 8000 healthz 200 | 留 compose + 注明手动起法 |
| P2 | CI yml + ruff + mypy + 测试矩阵 + coverage 门 + gitleaks + README/ADR(含 0003)/SECURITY/CONTRIBUTING | 超时外 | CI 本地 `act` 或平台 actions 可跑 | 留 .github 骨架 + commit 说明 |

**总 P0 ≈ 47min**；P1 是"可搬到对方系统"的真正决定项(API+前端+DB)，P2 是工程化终态。时间不够时**优先保 P1 前端五页骨架可见**——因为"不只是 API、是产品工作台"是这次核心判准，宁可后端某条 endpoint糙一点，也别让五页前端缺位。

> CLAUDE.md §4 守则：上面每行都有 verify，跑通即可独立确认，不需反复问。

---

## 8. README 必备段落（一眼归拢观感）

- 一句话定位 + 架构图(ASCII 或 mermaid)再现 PRD §1 主线。
- 快速上手: `make install / migrate / test / run / lint`。
- 域事实速查(§2 的"4 个坑 + 硬事实集")——你讲给面试官时的提词卡。
- ADR 索引 + 指向 `docs/adr/`。
- 安全说明指向 `SECURITY.md`。
- 诚实声明: 哪些是真跑(Persistence/XGBoost 若装)、哪些是 stub(LSTM/真平台对接/真爬虫)、合成行情来源与 seed。

---

## 9. 执行前最后自检清单（对照 PRD §3 担忧点逐条确认留痕）

- [ ] Settings 集中、无业务裸数字
- [ ] secret fail-fast + gitleaks + .env.example
- [ ] pytest + coverage 门
- [ ] CI yml 真跑 ruff/mypy/test
- [ ] 全 public 函数带类型, mypy --strict(core)
- [ ] 无裸 except, ProblemDetail 统一, 无回栈
- [ ] 结构化日志 + request_id, 无 print
- [ ] Pydantic 请求模型带约束
- [ ] JWT + scope + 限流 + CORS allowlist + 安全测试
- [ ] 锁文件/铁版本/hallucination: CI 从零装可跑
- [ ] 分层 + 层级 import 约束测试
- [ ] service 纯函数, router 薄
- [ ] 错误信封一致 + 形状测试
- [ ] Alembic baseline, 不用 create_all
- [ ] 参数化 SQL
- [ ] Clock 注入可冻结
- [ ] 无 speculative 抽象, ruff F401
- [ ] 外科手术 diff + 清晰 commit
- [ ] Makefile + README 零到运行
- [ ] Dockerfile 多阶段 + compose
- [ ] Timescale 模拟窄表/索引/time_bucket 等价/retention 配置(注释标生产)

---

## 10. 已定选型（用户拍板，不再问）

- 包管理: **uv**(`pyproject.toml` + `uv.lock`)。
- LP 求解器: **pulp**(对偶变量取 LMP)。
- Docker/CI: **本地必须真能跑通** `docker compose up`（backend+db+frontend 三服务);不是只留骨架。
- 语言: **中文为主**，关键领域术语保留英文(LMP/SCED/CfD/SCUC 等)以便面试双语切换。
- 前端: **加 Streamlit 产品工作台**(非 API 调试器)，五业务页;企业克制风，不过度花哨。
- **整体形态**: 直接可搬进对方系统的完整模块(后端+数据+产品工作台)，不是 API 集合。

执行 agent 依本 SPEC §7 优先级自驱推进，遇本节未涉及的细枝末节按 CLAUDE.md 四条自行判断并 commit 说明，**不再向用户追问**。里程碑(P0 各步、P1 前端五页可见、P2 docker 真跑)停下向用户报告。