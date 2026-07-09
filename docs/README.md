# 文档中心 · spark-pricing

电力现货交易端到端可交付模块的完整文档. 按角色索引:

## 按角色

| 你是 | 先看 |
|---|---|
| 交易员 / 分析师 / 结算员 | [使用手册 USER_GUIDE.md](USER_GUIDE.md) — 五个业务页怎么用 |
| 开发 / 集成方 | [接口文档 API.md](API.md) · [架构 ARCHITECTURE.md](ARCHITECTURE.md) |
| 运维 / 平台 | [部署 DEPLOYMENT.md](DEPLOYMENT.md) · [运维 OPERATIONS.md](OPERATIONS.md) |
| 安全 | [../SECURITY.md](../SECURITY.md) |
| 贡献者 | [../CONTRIBUTING.md](../CONTRIBUTING.md) |

## 全部文档

- **产品/需求**: [PRD.md](PRD.md) — 产品需求
- **技术规格**: [SPEC.md](SPEC.md) — 建什么、叫什么、映射什么
- **使用手册**: [USER_GUIDE.md](USER_GUIDE.md) — 面向业务用户
- **接口文档**: [API.md](API.md) — REST API 契约 (运行时 Swagger 在 `/docs`)
- **架构**: [ARCHITECTURE.md](ARCHITECTURE.md) — 分层、数据流、选型
- **部署**: [DEPLOYMENT.md](DEPLOYMENT.md) — Docker / 裸机两种路径
- **运维**: [OPERATIONS.md](OPERATIONS.md) — 巡检、监控、排障
- **架构决策 (ADR)**:
  - [0001 · SCED LP 取对偶当 LMP](adr/0001-sced-lp-cfd.md)
  - [0002 · 预测器接口](adr/0002-forecaster-interface.md)
  - [0003 · 前端做产品工作台](adr/0003-frontend-as-product.md)

## 快速上手

见根目录 [../README.md](../README.md) — 本地与 Docker 两种跑法、域事实速查、诚实声明.