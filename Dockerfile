#
# bestduo_AI — NLP Duo Coach
#
# Dual-role container:
#   1. Ollama 서버를 백그라운드로 띄우고 EXAONE GGUF 를 로드
#   2. FastAPI (uvicorn) 를 foreground 로 실행
#
# 이 구성은 Railway Hobby ($10-15/월) 단일 서비스 안에서 LLM 서빙 + HTTP API
# 양쪽을 RAM ~2GB 안에 끼워 넣기 위한 절충이다. 스케일 시 Ollama 를 별도 서비스로 분리.
#
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_MODELS=/root/.ollama/models \
    OLLAMA_KEEP_ALIVE=24h \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_MAX_LOADED_MODELS=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL https://ollama.com/install.sh | sh \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
      "fastapi>=0.115.0" \
      "uvicorn[standard]>=0.32.0" \
      "httpx>=0.27.0" \
      "redis[hiredis]>=5.1.0" \
      "asyncpg>=0.30.0" \
      "pydantic>=2.9.0" \
      "pydantic-settings>=2.6.0" \
      "prometheus-client>=0.21.0" \
      "structlog>=24.4.0" \
      "sentry-sdk[fastapi]>=2.18.0"

COPY app ./app
COPY scripts ./scripts
RUN chmod +x scripts/entrypoint.sh

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health >/dev/null || exit 1

ENTRYPOINT ["scripts/entrypoint.sh"]
