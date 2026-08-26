# 岗位能力图谱系统 —— 多阶段构建
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 依赖层（利用缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 代码层
COPY app ./app
COPY config ./config
COPY scripts ./scripts
COPY web ./web

# 运行时数据目录（首次启动会用内置 Mock 数据生成，或挂载真实数据卷）
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

# 默认命令：生成模拟数据 -> 一键评测 -> 启动服务
CMD ["sh", "-c", "python scripts/generate_data.py && python scripts/evaluate.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
