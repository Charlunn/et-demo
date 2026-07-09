# 贡献指南 · spark-pricing

## 一句话
本仓库是电力现货交易 **端到端可交付模块** demo; 改动遵循 CLAUDE.md 四条: 先想后写 / 简单优先 / 外科手术式改动 / 目标驱动可验.

## 如何本地跑
见 README.md "快速上手" (本地与 docker 两种跑法). 常用命令:
```bash
uv sync --extra dev                     # 装依赖
uv run alembic upgrade head             # 建表 (SQLite 本地或 Postgres)
uv run pytest --cov                     # 测试 + 覆盖门
uv run ruff check app tests scripts     # lint
uv run mypy                             # 严格类型 (core/domain/services)
uv run python -m app.cli backtest       # 跑主线产出 BacktestReport
uv run python -m app.cli serve          # 起后端 :8000
```
前端:
```bash
cd frontend && uv venv && uv pip install -r requirements.txt pytest
streamlit run app.py                    # 产品工作台 :8501
python -m pytest tests/test_smoke.py   # 烟测
```

## 改动原则 (SPEC §9 最后自检 + CLAUDE.md)
- **路由薄, service 纯函数**: 改动前确认职责落在正确层; 路由不导 SQLAlchemy, service 不导 FastAPI 类型 (有 `tests/test_layers.py` 守这条).
- **新增文件先问**: 它服务于 SPEC §1 主线哪一环或 §3 哪条担忧点?无则不做.
- **config 集中**: 业务门限/价差/时限/预算进 `core/config.py`, 业务代码零裸数字.
- **诚实标注**: 新模型走 Forecaster ABC; LSTM/stub/真平台对接/真爬虫一律在 backtest summary 与 README 声明.
- **迁移**: 改 ORM 改 Alembic 生成新 revision; **不在 prod 路径用 `create_all`**.

## Commit
小而外科手术式 diff; 只改与本次请求相关的行. commit 信息带: 理由 + scope + 测试/迁移说明.

> 本文件为简(short) 贡献指南 (SPEC §6 要求简短).