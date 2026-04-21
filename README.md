# bestduo_AI — NLP Duo Coach

BestDuo 의 자연어 질의 + LLM 설명 생성 서비스. `bestduo_BE` (Spring Boot) 의 사이드카로
Railway 위에서 동작하며, 아래 요소로 구성된다.

| Layer | 기술 |
| --- | --- |
| HTTP | FastAPI + uvicorn |
| LLM Serving | Ollama + EXAONE 3.5 2.4B Instruct (GGUF Q4_K_M, int4) |
| Cache | Redis (TTL 1h, 정규화 키) |
| Storage (read-only) | BestDuo PostgreSQL (공유) |
| Observability | Prometheus `/metrics`, Sentry |

> 전체 설계 배경·의사결정·위험은 [`my-wiki/wiki/synthesis/bestduo-duo-coach-plan.md`](../../my-wiki/wiki/synthesis/bestduo-duo-coach-plan.md) 참고.

---

## Phase 현황

- [x] **Phase 1** — FastAPI + Ollama sidecar, `/health`·`/metrics`, Railway 배포 + public domain verify 완료
- [ ] **Phase 2** — `champion_tags.json` + Intent Classifier + Entity Extractor + SQL 템플릿 + `POST /nlp/query` + Spring `FastApiNlpAdapter`
- [ ] **Phase 3** — `/nlp/explain` LLM 경로 + 환각 방어
- [ ] **Phase 4** — Prometheus 메트릭 + Resilience4j 연계 + Rate limit
- [ ] **Phase 5** — Human Eval (50 쿼리) + Ablation

### Phase 1 세부 체크리스트

- [x] FastAPI 스켈레톤 (`/health`, `/metrics`)
- [x] Ollama / Redis / Postgres 클라이언트 + 헬스 프로브
- [x] Dockerfile (ollama + fastapi 한 컨테이너, `zstd` 포함)
- [x] Railway entrypoint (모델 pull + warm-up + uvicorn)
- [x] Railway 배포 Active, Volume 마운트 (`/root/.ollama`), `${{ Postgres.DATABASE_URL }}` 치환
- [x] Public domain `/health` 전 구성요소 `up` 확인

---

## 로컬 개발

```bash
# 1. ollama 를 호스트에 설치하고 모델 pull (M 시리즈면 Metal GPU 가속)
brew install ollama
ollama serve &
ollama pull exaone3.5:2.4b-instruct-q4_K_M

# 2. 의존성 인프라만 컨테이너로
docker compose up -d   # postgres:5433, redis:6380

# 3. env 파일 준비
cp .env.example .env

# 4. 의존성 설치 + 실행
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# 5. 헬스체크
curl http://localhost:8000/health | jq
```

---

## 테스트

```bash
pytest
```

---

## Railway 배포 메모

1. Railway 프로젝트에 `bestduo_AI` 서비스를 추가하고 이 레포를 연결.
2. Dockerfile 기반 빌드 (Nixpacks 비활성화).
3. 환경변수는 `.env.example` 참고. 특히:
   - `DATABASE_URL` → `bestduo_BE` 와 같은 Postgres 인스턴스, 읽기 전용 역할로 분리 권장
   - `REDIS_URL` → `redis.railway.internal`
   - `INTERNAL_API_KEY` → Spring BE `NlpQueryPort` 의 아웃바운드 헤더와 공유
   - `OLLAMA_MODEL` 기본값 유지
4. Spring BE 에서 서비스 디스커버리는 Railway 내부 도메인 사용:
   `http://bestduo-ai.railway.internal:8000`.
5. 첫 배포 시 `ollama pull` 로 디스크 ~2GB 필요. Volume 붙여서 재배포마다 다시 받지 않도록.

---

## 디렉터리

```
bestduo_AI/
├── app/
│   ├── main.py        # FastAPI app factory + /health + /metrics
│   ├── config.py      # pydantic-settings 기반 env 로딩
│   └── clients.py     # Ollama / Redis / asyncpg 래퍼 + probe 함수
├── scripts/
│   └── entrypoint.sh  # ollama serve + 모델 pull + warm-up + uvicorn
├── tests/
│   └── test_health.py
├── Dockerfile
├── compose.yaml
├── pyproject.toml
└── .env.example
```
