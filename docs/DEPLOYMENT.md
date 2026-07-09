# 部署手册 · spark-pricing

> 面向运维 / 平台工程. 覆盖服务器上从零到运行的两条路径 (Docker Compose 推荐 / 裸机 systemd), 环境变量、密钥、反向代理、升级与回滚.

---

## 1. 部署形态总览

spark-pricing 是三服务模块:

| 服务 | 端口 | 说明 |
|---|---|---|
| `backend` | 8000 | FastAPI (uvicorn); 启动时自动 `alembic upgrade head` |
| `frontend` | 8501 | Streamlit 产品工作台; 经 `BACKEND_API_URL` 访问后端 |
| `db` | 5432 | PostgreSQL 16 (生产建议托管 RDS / 云数据库) |

推荐生产拓扑:

```
                 ┌───────────────────────────┐
   用户浏览器 ───▶│  反向代理 (Nginx/Caddy/ALB) │
                 │   :443  TLS 终止            │
                 └───────┬──────────┬──────────┘
                    /app │          │ /api
                         ▼          ▼
                  frontend:8501   backend:8000
                                      │
                                      ▼
                                   db:5432 (托管 PG)
```

---

## 2. 前置条件

| 项 | 版本 | 说明 |
|---|---|---|
| Docker Engine | ≥ 24 | Compose 路径 |
| Docker Compose | v2 | `docker compose` (非 `docker-compose`) |
| Python | 3.12 | 裸机路径 |
| uv | ≥ 0.11 | 裸机依赖管理 |
| PostgreSQL | 16 | 托管或自建 |

服务器最低配置 (demo/试运行): 2 vCPU / 4 GB RAM / 20 GB 磁盘. LP 求解与回测是 CPU 密集, 高并发回测时按需扩后端副本.

---

## 3. 路径 A · Docker Compose (推荐)

### 3.1 拉代码

```bash
git clone git@github.com:Charlunn/et-demo.git
cd et-demo
git checkout main
```

### 3.2 生成生产密钥并写 .env

`docker-compose.yml` 内置的 `SECRET_KEY` 仅供本地演示. **生产必须替换** (backend 有 fail-fast 校验: `DEBUG=false` 下用默认值/短于 32 字符会拒绝启动).

```bash
# 生成强密钥
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 写一个 .env.prod (compose 会读同目录 .env; 或用 --env-file)
cat > .env.prod <<'EOF'
DEBUG=false
SECRET_KEY=<粘贴上面生成的48字节密钥>
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=postgresql+asyncpg://spark:<强密码>@db:5432/spark
CORS_ORIGINS=["https://your-domain.com"]
DEMO_USER=trader
DEMO_PASSWORD=<强密码>
DEMO_SCOPES=backtest:run
DEFAULT_FORECASTER=persistence
LINE_FLOW_LIMIT_MW=80.0
RESERVE_REQUIREMENT_MW=20.0
BACKEND_API_URL=http://backend:8000
EOF
```

> ⚠️ `.env.prod` 含真实密钥, 不要提交 git (已被 `.gitignore` 覆盖 `.env*`). 生产用密钥管理 (Vault / AWS Secrets Manager / K8s Secret) 注入更佳.

### 3.3 起服务

```bash
docker compose --env-file .env.prod up --build -d
```

启动顺序由 compose 保证: `db` healthy → `backend` (自动跑 alembic 迁移) → `frontend`.

### 3.4 验证

```bash
curl -f http://localhost:8000/healthz          # {"status":"ok"}
curl -f http://localhost:8000/readyz           # {"ready":true,"db":"ok"}
curl -sf http://localhost:8000/docs -o /dev/null && echo "docs ok"
curl -sf http://localhost:8501 -o /dev/null && echo "frontend ok"
```

### 3.5 反向代理 (Nginx 示例)

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # 工作台 (Streamlit 需要 WebSocket)
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Request-ID $request_id;
    }
}
```

> 若走 `/api/` 前缀, 记得把 `CORS_ORIGINS` 与前端的 `BACKEND_API_URL` 调整为对应地址.

---

## 4. 路径 B · 裸机 systemd (不用 Docker)

### 4.1 后端

```bash
git clone git@github.com:Charlunn/et-demo.git /opt/spark-pricing
cd /opt/spark-pricing
pip install uv
uv sync                              # 生产不带 --extra dev
cp .env.example /opt/spark-pricing/.env   # 编辑: DEBUG=false + 强 SECRET_KEY + PG DATABASE_URL
uv run alembic upgrade head          # 迁移
```

`/etc/systemd/system/spark-backend.service`:

```ini
[Unit]
Description=spark-pricing backend
After=network.target postgresql.service

[Service]
WorkingDirectory=/opt/spark-pricing
EnvironmentFile=/opt/spark-pricing/.env
ExecStart=/opt/spark-pricing/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
User=spark

[Install]
WantedBy=multi-user.target
```

### 4.2 前端

```bash
cd /opt/spark-pricing/frontend
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
```

`/etc/systemd/system/spark-frontend.service`:

```ini
[Unit]
Description=spark-pricing frontend
After=network.target spark-backend.service

[Service]
WorkingDirectory=/opt/spark-pricing/frontend
Environment=BACKEND_API_URL=http://127.0.0.1:8000
ExecStart=/opt/spark-pricing/frontend/.venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --browser.gatherUsageStats false
Restart=always
User=spark

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now spark-backend spark-frontend
sudo systemctl status spark-backend
```

---

## 5. 数据库迁移

- 迁移由 Alembic 管理 (`alembic/versions/`); **禁止在生产用 `create_all`**.
- 后端 Docker 镜像启动命令已含 `alembic upgrade head`, 每次部署自动对齐 schema.
- 手动执行:
  ```bash
  uv run alembic upgrade head      # 升到最新
  uv run alembic current           # 查看当前版本
  uv run alembic downgrade -1      # 回退一版 (谨慎)
  ```
- 新增迁移 (改了 ORM 后):
  ```bash
  uv run alembic revision -m "描述" --autogenerate
  # 审查生成的 versions/*.py 再提交
  ```

---

## 6. 升级与回滚

### 升级

```bash
cd /opt/spark-pricing        # 或 et-demo
git fetch && git checkout <新tag或main>
# Docker:
docker compose --env-file .env.prod up --build -d
# 裸机:
uv sync && uv run alembic upgrade head && sudo systemctl restart spark-backend spark-frontend
```

### 回滚

```bash
# 代码回滚
git checkout <上一个稳定 tag>
# 若含迁移则先降级 DB 到该版本兼容的 revision
uv run alembic downgrade <target_revision>
# 重启服务 (同升级)
```

> 建议每次发布打 tag (`git tag -a v0.1.0 -m ...`), 回滚时直接 checkout tag.

---

## 7. 备份

- **数据库**: 定时 `pg_dump`:
  ```bash
  pg_dump -U spark -d spark -Fc -f /backup/spark_$(date +%F).dump
  ```
- Docker volume `spark_pgdata` 是数据落盘位置; 生产建议改用托管 PG 并启用自动快照.
- 合成行情由固定 seed 复现 (`scripts/seed_demo.py`), 无需备份.

---

## 8. 相关文档
- 运维 / 监控 / 排障: [OPERATIONS.md](OPERATIONS.md)
- 接口契约: [API.md](API.md)
- 架构: [ARCHITECTURE.md](ARCHITECTURE.md)
- 安全: [../SECURITY.md](../SECURITY.md)