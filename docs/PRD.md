# PRD · 电力现货交易"小而美"Demo（职级精品）

> 目的：用约 1 小时交付一个**让面试官心悦诚服、加分**的电力现货交易指尖模块。它不是要复刻一整个交易平台，而是用**1 条端到端业务主线**证明：
> 「我会搭建生产质量、可维护、安全、有领域可信度的电力交易代码，且我的工程风格比你们现在写的更干净。」

---

## 0. 策略定位（这决定了 demo 长什么样）

**面试方真正缺的，不是再一个"懂交易规则的人"（他们有人懂），而是能把"智慧平台"想法快速落地、交付质量高于内部手写的人。** 你的差异化价值 = 工程交付力 × AI 驾驭力，不是领域背诵力。

因此被对方真正观感的，会排序评估 demo 在下面**三个层级**上的得分：

| 层级 | 观感信号 | 一旦失分会被贴的标签 |
|---|---|---|
| **A. 组织一眼规整** | 包结构、命名、模块分层、注释密度、pyproject/锁文件、CI | "随手写的，靠 prompt 凑出来的" |
| **B. 安全可放心上线** | secret 走 env、输入校验、Auth、限流、CORS、日志、错误信封 | "AI 写的东西不能上生产" |
| **C. 可读可交接** | 小而清晰的 commit、测试、README + 架构图、OpenAPI、ADR | "没人接得住" |

**只要 A/B/C 全部拿到 A，领域只要"无错"即可（无需万字背诵）**——你要的是"这模块能直接拿去用，作者明显能托付"的状态。反过来说，领域文案写得再漂亮，一旦 A/B/C 任何一项露馅，面试官会立刻判定"AI 凑的，放生产 = 风险"，这才是对方最常担心的"AI 代码能否上线"那个点。

> **交付物的形态定义（务必记牢）**：这次要交付的是一个**完整的、可直接搬进对方系统的模块**——后端 + 数据 + 一个电力交易员/分析师**真正会用的工作台前端**。前端的判准是：把它交给一个不懂 API 的人，他能走完"看行情 → 做报价 → 看出清 → 对账 → 复盘"整条真实业务路径，**而不是**点"发送请求 / 看 JSON 响应"这种调试器动作。换句话说，前端是产品的脸，不是 Postman 的脸。这一条是这次的核心，不是可选项。

> 与 CLAUDE.md 一致：**做小不做大、不过度抽象、改的人就是改的，干净。** demo 不留你自己后续用不到的 speculative 功能。

---

## 1. 一条业务主线（一切功能都挂在它下面，不发散）

```
负荷预测/可再生能源出力
        │  (输入)
        ▼
【日前报价】 报价策略模块  ──产出 报价(电池)──▶ 生成分段报价曲线(≤10段)
        │
        ▼
【日前出清】 出清引擎(energy+旋转备用 联合出清, LP)
        │  ──产出 日前计划电量 + 节点LMP(能量价/阻塞价/损耗价 来自LP对偶变量)
        ▼
【双结算】 结算模块  ──日前=计划电量×日前LMP; 实时偏差=(实际-日前计划)×实时LMP; 中长期差价合约=(合约价-现货参考价)×合约量
        │
        ▼
【回测/复盘】 回测模块 ── PnL/命中率/信息比率/出清价MAPE/最大回撤, 对标"报边际成本"基准策略
        │  (一条产出: BacktestReport)
        ▼
 提交报价决策 → 策略在历史行情上跑出的业绩报告(给HR/面试官看的"业绩单")
        │
        ▼
【工作台前端】 电力交易员真实使用场景的整个面板（见 §2.1）
```

**这条主线一句话讲清就够定魂**："我把电力现货交易的全链路打通了，从预测→报价→出清→结算到回测，并且把它包成一个电力交易员真正会用的工作台，这个模块能整体搬进你们的系统。"

> 这条主线**精确覆盖**了 JD 的核心动词：行情数据建模、负荷预测、报价策略、价格预测、出清、清算结算、实时数据处理、回测复盘——每一个都映射到真实代码模块，无虚词。

---

## 2.1 前端"真实使用场景"（不是 API 测试页——这是这次的核心判准）

判定准则：把页面给一个不懂 API 的人，他能不能走完下面这条真实业务操作路径。能 = 合格；若人看到的是"发送 Post / 清空 body / status 200 / JSON 列出来"的手感 = 全盘失败，做成 Postman 了。

工作台分若干**业务 tab**（不是技术 tab），每个 tab 承载一段业务动作、把"调谁接口 / 显示什么 / 能改什么 / 点完看到什么"讲死，严禁变成一群调试按钮：

| 业务 tab | 这是谁在用 | 他来这里干什么 | 页面呈现什么 | 操作后看到什么 |
|---|---|---|---|---|
| **行情看板** | 交易员/分析师 | 看当前电价 & 历史走势 | 多节点日 LMP 折线 + 实时滚动 tick(模拟）+ 负荷OfDay分布;阻塞(no)标记 | 选节点/时段范围 → 图刷新;点"导出本段行情"→ 下载 csv |
| **报价工作台** | 交易员 | 给自己手里的机组做一份分段报价 | 机组列表(含成本曲线证)+ 分段报价表格(≤10段, 行=时段, 列=价/量) + 风险加成/策略选择参数(图表) | 选策略 → 自动填报价表;改风险参数 → 表实时重算;点"提交报价" → 报价进入待出清队列 |
| **出清与计划** | 调度/交易 | 触发或查看本次出清与每机组出力计划 | 出清结果:每节点LMP(能量价/阻塞价/损耗价) + 每机组计划出力P与旋转备用R + 网络阻塞可视化(哪个节点限) | 点"运行出清" → 进度→ 出清结果表+图;点某时段 → 看该时段调楼层 |
| **结算与对账** | 结算员 | 看本周期该收该付款 | 三层收付款明细(日前结算/实时偏差/中长期Diff) + 每层金额 + 合计 + 与手算口径一致性标注 | 给入实际电表数 → 实时偏差;选中长期合约 → 差价;点"生成结算单"→ 可导出 |
| **回测与复盘** | 分析师/交易员 | 跑两条策略对比业绩 | 两条策略的PnL曲线、命中率、盈亏比、信息比率、出清价MAPE、最大回撤 对照表 + 一段中文自然语言小结 | 选历史区间 → 选两条策略 → 运行 → 图表+指标+小结;点"导出复盘报告"|

**前端风格基调（背记）**：好看但**不过度花哨**；**企业感但不死板老式**。具体：
- 视觉: 大量留白 + 克制的深色/中性辅色 + **单一品牌主色**(取一个稳的电电力蓝/青绿系, 不彩虹)、卡片化、细边、轻投影; 不要透视感发光、不要诗意渲染。
- 字体: 一个无衬线(Inter/系统字体栈) + 数字用 mono 对齐; 不混多种字体。
- 图表: 折线/柱状为主, 配色不超5, 网格细且半透明, 永远带轴线单位; 不开发炫图(不实Tooltip全量、不动画逐点切)。
- 交互: 加载态/空态/错误态都有; 关键按钮在提交前变灰; 没完的加载用骨架屏不得持续。 **企业稳可靠第一。**
- 技术栈: Streamlit 单文件多页(快速且自带企业感卡片/表格/图表; 避免重型SPA)。应对: 一个工作表"页面布局"+ 顶部导航 + 业务页 + 统一颜色主题(`.streamlit/config.toml`)。 **不用 React/Next SPA(1h 内不入不动)。**

> ⚠️ **对前端的 CLAUDE.md 守则**: 不炫技、不过度组件化、不堆没用的小件; 每个可见元素都要能指回某个业务动作。前端 **是产品脸不是调试器;面对客户面对用户不是面对开发者。这是你不像"AI 凑的"的最后一冲。**

---

## 2. 域事实（已做对抗性核实，避免领域露馅）

> 这些是 demo 必须 **背记准确、且能解释** 的关键域事实。验证已挑出 4 个常见坑位，**务必避开**：

- ✅ **DFC 出清是 LP 优化、取约束对偶变量当 LMP，不是"撮合配对"。** 撮合属于中长期，现货出清是优化。这是最露馅的分水岭。
- ✅ **LMP = 系统边际能量价 + 阻塞价 + 损耗价**，按节点算；统一出清(LMP uniform)不是一个东西——别混说。
- ✅ **双结算** = 日前(计划电量×日前LMP) + 实时偏差((实际−日前计划)×实时LMP)，**避免双重计价**。
- ✅ **中长期 = 金融差价合约(CfD)**，物理交付解耦，按"合约价 − 省级现货参考价"结算；**三层收益 = 中长期差价 + 现货日前 + 现货偏差**。
- ⚠️ **实时市场是"全网滚动再调度(SCED)，但只对偏差电量按实时LMP结算"**——别跟"实时市场只处理偏差"的笼统说法混淆。**重新调度的范围是全网，只有偏差电量计价用实时价**。面试官爱追问的就是这条缝。
- ⚠️ **联合出清 = 能量 + 旋转备用一起优化；调频/AGC 通常是单独的辅助服务市场**，未必同优化。demo 只联合**一个旋转备用**，明确标注"调频在此简化，不上 AGC"。
- ⚠️ **集中式代表省份**: 广东/山西/山东/蒙西；**浙江是分散式代表**。四川是水电为主、争议大——demo 里若举例子用广东/山西，**避免把四川列为集中式铁板钉钉**。
- ⚠️ **日前粒度统一用 15 分钟(96段)**，不要含糊提"有的省用小时制"。

demo 设定的"硬事实集"，作者必须能在面试时不假思索地讲出差分：
- 5 台机 + 2 节点(1 参考 / 1 负荷)，其中节点间线路有容量上限 → 制造真**阻塞**。
- LP (固定机组组合, 即 SCED 经济调度层)，**LMP 直接读 LP 对偶变量**，不做 merit-order 凑数。
- 能量 + 1 个旋转备用联合出清；调频明确略去。
- 15 分钟 × 96 时段；实时"简化为同样 15 分钟，注释说明生产为 5 分钟滚动"。
- 1 个差价合约(CfD)，覆盖中长期那一层。

---

## 3. AI 代码担忧点的预射（在文档/实测上都得能看到被拍到）

> 这是对方决定"敢不敢用 AI/敢不敢要你"的隐性考点。每一项在代码与 CI 里都要留下工程师能认出的"应对痕迹"。

| 担忧 | 在本 demo 的应对痕迹（须可被一眼看到） |
|---|---|
| 魔法数字散落 | `core/config.py` 用 Pydantic v2 `BaseSettings`，所有门限/价差/时限/预算都从 env 读，业务代码零裸数字 |
| 硬编码 secret | `.env.example` 提交、`.env` 入 .gitignore；`SECRET_KEY` 有**失败即失败(fail-fast)校验**：prod 下等于默认值/过短直接拒；CI 跑 gitleaks |
| 无测试 | pytest + httpx AsyncClient；service 层纯函数 parametrized；route 覆盖 happy/422/401/404；`--cov-fail-under` 门限 |
| 无 CI | `.github/workflows/ci.yml`：ruff check + format --check + mypy + pytest + coverage，任一非零即失败 |
| 类型薄弱 | `from __future__ import annotations`；所有 public 函数带类型；mypy --strict 跑在 core 模块 |
| 异常被吞 | 无裸 `except:`；service 抛领域错误，FastAPI `exception_handler` 统一映射成 RFC7807 ProblemDetail，绝不回栈 |
| 无日志 | `core/logging.py` 结构化 JSON 日志 + request-id 中间件，记 method/path/status/duration_ms；业务里无 `print()` |
| 输入不校验 | 所有 endpoint 接 Pydantic v2 请求模型，带 `Field(gt=, max_length=,)` 约束，service 层只见可信数据 |
| 无安全态势 | OAuth2/JWT `Depends`、scope 校验 dependency、CORS allowlist from settings、slowapi 限流写在 auth/写接口；有一条测试断言未授权 → 401/403 |
| 幻觉库/API | `pyproject.toml` 用锁文件；只选主流稳定库；CI `pip install` 从零可重装并跑测试，证可解析 |
| 单体一团 | `api/routes → services → repositories → models/schemas`；路由不导 SQLAlchemy、service 不导 FastAPI 类型；有 import 层级约束 |
| 业务逻辑糊在 HTTP 层 | service 为纯函数，吃 domain/dataclass、吐 domain 对象；router 极简(解析→调 service→装响应) |
| 出错信封不一致 | RFC7807 `{type,title,status,detail,instance,request_id}` 全局 handler，并有断言其形状的测试 |
| 无迁移 | Alembic 接 `Base.metadata`，baseline revision；CI `alembic upgrade head`；**不用 `create_all`** |
| SQL 注入 | SQLAlchemy 2.0 全用参数化 `text()`，无 f-string SQL |
| 时钟不可测 | `Clock` 时间提供者 via `Depends`，业务不直接 `datetime.now()`，测试可冻结时间 |
| speculative 抽象 | 每模块/endpoint 都能指回 §1 主线一条需求；ruff F401 拒未用 import；死码注释在 PR body 或删 |
| 提交不干净 | 小而外科手术式 diff，不改无关代码；commit 信息带理由+scope+测试+迁移说明 |
| 不可复现本地 | Makefile：`make install/test/migrate/run/lint`；README 零到运行 copy-paste 路径 |
| 无容器 | 多阶段 Dockerfile + docker-compose 起 DB；有 .dockerignore |
| 集成不可信 | Timescale hypertable 用 SQLAlchemy 模拟：窄表(time,node,series,value) + (node_id,ts DESC) 索引 + `time_bucket` 等价聚合 view + 保留策略配置对象(注释标"生产才 create_hypertable") |

---

## 4. 范围与不做（Explicitly out of scope）

- ❌ 跨省跨区 / 省间现货
- ❌ 调频/AGC/黑辅
- ❌ UC 整数搜索(只做 SCED 经济调度层, LP)，**但注释/ADR 要说明这一点取舍及其含义(对LMP仍真实有效)**
- ❌ 损耗(LMP 损耗分项设 0 或单损耗因子；阻塞才是 . 须示出的部分)
- ❌ LSTM 真训练(重依赖、1h 装不上；走 Forecaster 接口 stub，注释明示)
- ❌ 真实交易平台对接 / 真爬虫(会超时且有风控/反爬，demo 用合成的可复现行情)
- ❌ ARIMA/XGBoost 若装不上也别硬上——接口在，默认 PersistenceForecaster 实跑，XGBoost 作为"可选安装包"再选

---

## 5. 成功标准（goal-driven，可独立验）

1. `make install && make migrate && make test` 一条命令从零到测试全绿 → verify: CI 复现该过程
2. `python -m demo.cli backtest` 跑出一份 `BacktestReport`，含 PnL/命中率/信息比率/出清价MAPE/最大回撤，策略胜过"报边际成本"基准 → verify: 测试断言 report 字段非空且 PnL 有限
3. `python -m demo.serv` 起 FastAPI，Swagger /docs 全部 endpoint 带类型+示例；`/healthz` `/readyz` 200 → verify: route 测试 + 一次 curl
4. 出清引擎对给定算例返回的 LMP 与手算 LP 对偶一致 → verify: parametrized 出清测试
5. 结算的三层收益与按公式手算一致 → verify: 结算单测
6. 安全：未授权 → 401、越权 → 403，且 CI 有 gitleaks 与 secret fail-fast 测试 → verify: auth 测试通过

---

## 6. 交付物清单（"配套的东西全与企业级对齐"）

- 源码: 分层包(`app/api`, `app/services`, `app/domain`, `app/models`, `app/schemas`, `app/core`, `app/db`)
- `tests/` 镜像分层
- `pyproject.toml`(锁) + `requirements*.txt`(pin) + `.python-version`
- `alembic/` + baseline
- `.github/workflows/ci.yml`
- `Dockerfile` + `docker-compose.yml`(含 `backend`+`db`+`frontend` 三服务) + `.dockerignore`
- `Makefile`
- `.env.example` + `.gitignore`
- `README.md`(快速上手/架构图/ADR索引) + `docs/adr/0001-sced-lp-cfd.md`、`docs/adr/0002-forecaster-interface.md`、`docs/adr/0003-frontend-as-product.md`
- `SECURITY.md`、`CONTRIBUTING.md`(简短)
- `openapi.json` 快照(可选)
- **前端 `frontend/`**: Streamlit 多页工作台(见 §2.1 的 5 个业务 tab)、`.streamlit/config.toml`(主题、品牌色)、各页与后端 API 解耦的轻量客户端 `frontend/api_client.py`、`frontend/README.md`(说明这是产品工作台、不是 API 调试器)。docker-compose 中 `frontend` 服务暴露 `localhost:8501`。

---

## 7. 风险与陷阱（执行时盯死）

- **时间风险**: 1h 内做不完全套——必须按优先级裁。见 SPEC 的"实施优先级与1h裁剪表"。先把 A 层(组织+安全核心)与主线打通跑出报告，B/C 层(完整CI/Docker/ADR)若超时则保留文件骨架并以 commit 说明。
- **领域露馅**: 严格遵守 §2 的 4 个坑：撮合≠出清、实时全网重调但只对偏差计价、调频不同优化、四川别列集中式铁板。
- **过度工程**: 严守 CLAUDE.md §2/§3——不做 JD 没要求的扩展、不"顺手美化"无关码。每新增文件先问"它服务于 §1 主线哪一环或 §3 哪条担忧点?"。
- **依赖地狱**: 装不出就立刻降级到 PersistenceForecaster stub，**绝不让依赖装不上拖垮 1h**。