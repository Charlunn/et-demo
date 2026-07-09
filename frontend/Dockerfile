# spark-pricing 前端: Streamlit 产品工作台 (SPEC §3.7).
FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先装依赖 (利用缓存)
COPY frontend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend ./frontend
WORKDIR /app/frontend

ENV BACKEND_API_URL=http://backend:8000

EXPOSE 8501

# gatherUsageStats=false 避免 streamlit 遥测 (SPEC §3.7.5).
CMD ["streamlit", "run", "app.py", "--server.port", "8501", \
     "--server.address", "0.0.0.0", "--browser.gatherUsageStats", "false"]