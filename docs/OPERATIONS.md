# 运维手册 · spark-pricing

> 面向 SRE / 值班. 覆盖日常巡检、监控指标、日志、常见故障排查、扩缩容、密钥轮换.

---

## 1. 健康检查

| 检查 | 命令 | 期望 |
|---|---|---|
| 存活 | `curl -f http://<host>:8000/healthz` | 200 `{"status":"ok"}` |
| 就绪 (含 DB) | `curl -f http://<host>:8000/readyz` | 200 `{"ready":true,"db":"ok"}`; DB 断 → 503 |
| 前端 | `curl -f http://<host>:8501` | 200 |
| 容器状态 | `docker compose ps` | 三服务 Up, db healthy |

将 `/healthz` 配为 LB/K8s 的 liveness, `/readyz` 配为 readiness (它会探 DB).

---

## 2. 日志

- 后端用 **structlog 结构化日志**. `DEBUG=true` → 彩色控制台; `DEBUG=false` (生产) → JSON 行, 便于日志采集 (Loki/ELK/CloudWatch).
- 每条 HTTP 日志含: `request_id / method / path / status / duration_ms`.
- 每个响应回传 `X-Request-ID` 头; 用户报错时取该 ID 反查日志.

```bash
# Docker 看日志
docker compose logs -f backend
docker compose logs --tail=200 backend | grep '"status": 5'   # 找 5xx

# 按 request_id 追踪
docker compose logs backend | grep '<request_id>'
```

- 业务代码无 `print()`; 兜底异常记 full stack 到服务端, 对外只回 ProblemDetail (不泄栈).

---

## 3. 监控指标 (建议接入)

当前 demo 未内置 Prometheus exporter (超出 SPEC 范围). 生产建议补:

| 指标 | 来源 | 告警阈值建议 |
|---|---|---|
| HTTP 5xx 率 | 日志 status 字段 | > 1% 持续 5 分钟 |
| P95 延迟 | 日志 `duration_ms` | `/clearing` `/backtest` 是 CPU 密集, 单独看 |
| `/readyz` 失败 | 探针 | 连续 3 次 → 页 |
| DB 连接数 / 慢查询 | PG `pg_stat_activity` | 接近 max_connections |
| 容器重启次数 | Docker/K8s | 非零即查 |

> 接入方式: 在 `LoggingMiddleware` 已有 duration_ms, 可加 `prometheus-fastapi-instrumentator` 暴露 `/metrics` (一行中间件, 属后续增强).

---

## 4. 常见故障排查

### 4.1 backend 起不来, 退出码 1

```bash
docker compose logs backend | tail -40
```
常见原因:
| 现象 | 原因 | 处理 |
|---|---|---|
| `SECRET_KEY 必须...` | `DEBUG=false` 用了默认/短密钥 | 换强密钥 (§DEPLOYMENT 3.2) |
| `function time_bucket ... does not exist` | 误用 TimescaleDB 函数 | 已修: 原生 PG 用 `date_trunc`; 确认代码为最新 |
| `connection refused` (db) | db 未 healthy 先起了 backend | compose 已配 `depends_on healthy`; 检查 db 日志/密码 |
| `alembic ... target database is not up to date` | 迁移未跑 | `docker compose exec backend alembic upgrade head` |

### 4.2 /readyz 返回 503

DB 不可达. 查:
```bash
docker compose exec db pg_isready -U spark
docker compose exec backend python -c "import os;print(os.environ['DATABASE_URL'])"
```
确认 `DATABASE_URL` 主机名 (compose 内应为 `db`), 密码, 网络.

### 4.3 前端能开但操作报"后端不可达"

前端经 `BACKEND_API_URL` 调后端. 检查:
```bash
docker compose exec frontend python -c "import os;print(os.environ['BACKEND_API_URL'])"
# compose 内应为 http://backend:8000
```

### 4.4 登录失败 401

核对 `DEMO_USER` / `DEMO_PASSWORD` 环境变量与输入一致.

### 4.5 429 限流

正常保护. 若合法流量被误伤, 调 `app/api/routes/*.py` 里 `@limiter.limit(...)` 的额度并重新部署.

### 4.6 出清返回 422 Clearing infeasible

负荷 / 备用 / 线路约束冲突 (如线路上限太小导致负荷节点无法满足). 提示用户放宽 `line_flow_limit_mw` 或降低负荷.

---

## 5. 扩缩容

- **后端无状态** (报价队列目前进程内; 生产多副本前需将其迁到 DB — 见 `repositories/bid.py` 已备好). 可水平扩 uvicorn `--workers` 或多容器副本 + LB.
- **回测/出清 CPU 密集**: 高并发时后端 CPU 是瓶颈, 优先纵向 (更多 vCPU) 或限并发.
- **前端** Streamlit 单进程有会话态, 多副本需 sticky session (LB 按 IP 亲和).
- **DB**: 生产用托管 PG, 按连接/存储扩.

---

## 6. 密钥轮换

```bash
# 1) 生成新 SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"
# 2) 更新 .env.prod / 密钥管理
# 3) 滚动重启 backend
docker compose --env-file .env.prod up -d backend
```
> 轮换 `SECRET_KEY` 会使所有现有 JWT 立即失效, 用户需重新登录. 选低峰期执行.

---

## 7. 备份与恢复

见 [DEPLOYMENT.md §7](DEPLOYMENT.md). 恢复:
```bash
pg_restore -U spark -d spark -c /backup/spark_2024-01-01.dump
```

---

## 8. 例行巡检清单 (日/周)

- [ ] 三服务 `docker compose ps` 全 Up
- [ ] `/healthz` `/readyz` 200
- [ ] 近 24h 5xx 率、P95 延迟在阈值内
- [ ] DB 磁盘 / 连接数余量
- [ ] 备份任务成功产出 dump
- [ ] 证书有效期 (反代 TLS)
- [ ] 依赖安全公告 (定期 `uv sync` + CI gitleaks)

---

## 9. 相关文档
- 部署: [DEPLOYMENT.md](DEPLOYMENT.md)
- 接口: [API.md](API.md)
- 架构: [ARCHITECTURE.md](ARCHITECTURE.md)
- 安全: [../SECURITY.md](../SECURITY.md)