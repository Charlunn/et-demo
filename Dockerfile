# spark-pricing 后端: 多阶段 builder -> slim (SPEC §6 / §10 docker 本地必跑).
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# 装 uv
RUN pip install --no-cache-dir uv==0.11.26

WORKDIR /app

# 先只拷依赖清单与 readme (uv sync 构建可编辑 wheel 需 readme + 包名), 利用缓存
COPY pyproject.toml README.md ./
COPY uv.lock* ./

# 同步依赖到 .venv (含 dev 组以便 alembic/pytest; 生产可分离).
RUN uv sync --extra dev

# ---- runtime ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts
COPY .env.example ./env.defaults

EXPOSE 8000

# 启动前跑 alembic upgrade head (SPEC §4.6); 然后 uvicorn.
# DEBUG 默认 false (生产), SECRET_KEY 必须由 env 注入 (fail-fast, SPEC §4.1).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]