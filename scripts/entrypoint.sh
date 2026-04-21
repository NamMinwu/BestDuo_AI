#!/usr/bin/env sh
set -eu

MODEL="${OLLAMA_MODEL:-exaone3.5:2.4b-instruct-q4_K_M}"
PORT="${APP_PORT:-8000}"

echo "[entrypoint] starting ollama server..."
ollama serve &
OLLAMA_PID=$!

# ollama 가 포트 뜰 때까지 대기 (최대 30초)
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! kill -0 "$OLLAMA_PID" 2>/dev/null; then
  echo "[entrypoint] ollama failed to start" >&2
  exit 1
fi

echo "[entrypoint] ensuring model is available: $MODEL"
if ! ollama list | awk '{print $1}' | grep -q "^${MODEL}$"; then
  ollama pull "$MODEL"
fi

# 워밍업: 모델을 RAM 에 상주시켜 첫 요청 cold-start 제거
echo "[entrypoint] warming up model..."
curl -fsS -X POST http://127.0.0.1:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"prompt\":\"hello\",\"stream\":false,\"keep_alive\":\"24h\"}" \
  >/dev/null || true

echo "[entrypoint] starting fastapi on :$PORT"
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --proxy-headers \
  --forwarded-allow-ips='*'
