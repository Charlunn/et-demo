"""spark-pricing: 电力现货交易端到端可交付模块.

包结构 (SPEC §2):
  app/api/routes   薄路由 (解析 -> service -> 装响应)
  app/services     纯业务逻辑 (不导 FastAPI 类型, 不直接建 session)
  app/domain       纯领域对象 + 算法 (无 IO, 最易测)
  app/models       SQLAlchemy 2.0 ORM
  app/schemas      Pydantic v2 请求/响应
  app/repositories DB 访问唯一去处
  app/core         横切关注点: config/logging/security/clock/errors
  app/db           engine/session/timeseries
"""

__version__ = "0.1.0"