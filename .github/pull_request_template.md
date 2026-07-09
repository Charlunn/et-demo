## 变更说明 / What & Why

<!-- 这次改了什么、为什么改. 关联 SPEC §? / issue #? -->

## 类型

- [ ] 功能 (feature)
- [ ] 修复 (fix)
- [ ] 重构 (refactor, 行为不变)
- [ ] 文档 (docs)
- [ ] 工程/CI (chore)

## 测试 / Verification

<!-- 跑了什么、结果如何. 贴关键输出 -->

- [ ] `uv run pytest --cov` 绿 (覆盖门 ≥80)
- [ ] `uv run ruff check` + `ruff format --check` 绿
- [ ] `uv run mypy` 绿 (core/domain/services strict)
- [ ] 涉及 DB: `uv run alembic upgrade head` 绿 + 新迁移已审查
- [ ] 涉及前端: `frontend` 烟测绿
- [ ] 涉及部署: `docker compose up --build` 本地跑通

## 检查单 (CLAUDE.md 四条 + SPEC §9)

- [ ] 先想后写: 假设已明确, 无静默歧义
- [ ] 简单优先: 无 speculative 抽象/多余功能
- [ ] 外科手术式: 每个改动行可追溯到本次需求, 未顺手改无关代码
- [ ] 分层守则: 路由不导 SQLAlchemy, service 不导 FastAPI (test_layers 绿)
- [ ] 配置集中: 无业务裸数字; secret 走 env
- [ ] 诚实标注: stub/真跑在 summary 与 README 一致

## 迁移 / 破坏性变更

<!-- 有则说明升级与回滚步骤; 无则写 "无" -->
无