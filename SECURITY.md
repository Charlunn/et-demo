# 安全说明 · spark-pricing

> demo 项目, 安全设计已留痕可被一眼认出, 但**不是生产级硬化**. 真平台请替换 IdP、密钥管理与限流后端.

## 已落地的安全应对 (SPEC §4 / PRD §3 担忧点)

| 担忧 | 应对痕迹 |
|---|---|
| 硬编码 secret | `.env.example` 提交占位值; `.env` 在 `.gitignore`; `SECRET_KEY` **fail-fast** 校验 (非 debug 下默认值/短于32/含 `*` 直接拒启动); CI 跑 gitleaks |
| Auth | `OAuth2PasswordBearer` + JWT(HS256); `get_current_user` Depends; `require_scope("backtest:run")` 守写端点; 无 token→401, 越权→403 (有断言测试) |
| 限流 / CORS | `slowapi` 挂在 auth/写端点; CORS allowlist 来自 settings, **通配 `*` 被拒** (有断言测试); prod 默认空 allowlist |
| 输入校验 | 全部 endpoint 接 Pydantic v2 请求模型, `Field(ge/le/max_length)` 约束; service 层只见可信数据 |
| 异常泄栈 | 全局 exception handler 把 `DomainError`/`HTTPException`/`RequestValidationError`/兜底 `Exception` 统一映射为 RFC7807 ProblemDetail; **兜底绝不回栈**, 服务端 log full |
| 时钟 | `Clock` 经 Depends 注入, 业务不直接 `datetime.now`, 测试可冻结 |
| SQL 注入 | SQLAlchemy 2.0 全参数化 (`text()` + 绑定参数), 无 f-string SQL |

## demo-only 取舍 (诚实标注)
- 密码比对为**明文等值** (`demo_user`/`demo_password` 在 env), 仅 dev test user; 生产须走哈希/外部 IdP.
- JWT HS256 对称密钥; 真平台多服务应改非对称/外部签发.
- `.env` 的 `SECRET_KEY` 在 docker-compose 内给了演示值, 仅用于本地 `docker compose up`; 生产必须由密钥管理注入.

## 报告
安全相关问题请基于本文件对应条目核对, demo 级不设漏洞赏金流程.