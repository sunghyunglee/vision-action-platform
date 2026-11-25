# Operations

> 기준: `compose.yaml` · `.env.example` · `backend/config/settings.py` (40d3916)

## 1. 실행

준비: Windows 11 + WSL2 Ubuntu + Docker Desktop (WSL integration 켜기). GPU 없이 CPU 로 동작합니다.

```bash
git clone https://github.com/sunghyunglee/vision-action-platform.git
cd vision-action-platform

# 모델 2개는 Git 에 없음 → 학습 프로젝트 결과물에서 복사
cp <학습 프로젝트>/rf_action_baseline.joblib ai_service/models/
cp <학습 프로젝트>/yolo11n-pose.pt          ai_service/models/

cp .env.example .env                 # SECRET_KEY · DB 비밀번호 · IP Webcam 주소를 바꿈
docker compose up --build -d         # 5개 서비스 (django 가 migrate 를 먼저 실행)
docker compose ps                    # postgres · redis · fastapi · django = healthy, celery = running
docker compose exec django python manage.py createsuperuser
docker compose exec django python manage.py test     # 51 tests · OK
```

끄기: `docker compose down` (볼륨 유지) · DB 까지 지우기: `docker compose down -v`

## 2. 서비스 · 포트 · 볼륨

| 서비스 | 포트 | 볼륨 | healthcheck | 기다리는 서비스 |
|---|---|---|---|---|
| `postgres` | 공개 안 함 | `postgres_data:/var/lib/postgresql/data` | `pg_isready` · 5초 | — |
| `redis` | 공개 안 함 | — | `redis-cli ping` · 5초 | — |
| `fastapi` | `127.0.0.1:8001` (내 PC 에서만) | `./ai_service/models:/app/models:ro` | `GET /health` · 10초 · start 30초 | — |
| `django` | `8000` | `media_data:/app/media` | `GET /api/v1/health/` (DB · Redis) · 10초 | postgres · redis healthy |
| `celery` | 공개 안 함 | `media_data:/app/media` | — | postgres · redis · fastapi healthy |

- 컨테이너끼리는 서비스 이름 (`postgres` · `redis` · `fastapi`) 으로 통신합니다. `localhost` 가 아닙니다.
- `django` 와 `celery` 는 같은 이미지이고 `media_data` 를 함께 씁니다 (Django 가 저장한 업로드 영상을 Worker 가 읽음).
- `TZ=Asia/Seoul` 은 fastapi · django · celery 의 **로그 시각**만 KST 로 맞춥니다. DB 는 `USE_TZ=True` 로 UTC 저장.
- 증거: [evidence/logs/compose_ps_v1.txt](evidence/logs/compose_ps_v1.txt) (django 도 healthy) · 개선 전 [compose_ps.txt](evidence/logs/compose_ps.txt)

## 3. `.env` 항목

| 묶음 | 키 | 기본 · 예시 | 설명 |
|---|---|---|---|
| FastAPI | `MODEL_DIR` · `RF_MODEL_FILE` · `RF_COLUMNS_FILE` · `RF_INFO_FILE` | `/app/models` · 파일 이름 3개 | 모델 위치 |
| | `POSE_WEIGHTS` · `POSE_DEVICE` | `yolo11n-pose.pt` · `cpu` | |
| Django | `DJANGO_SECRET_KEY` | 바꿔서 사용 | |
| | `DJANGO_DEBUG` | `True` | **시연 설정** · 운영은 False |
| | `DJANGO_ALLOWED_HOSTS` · `DJANGO_CSRF_TRUSTED_ORIGINS` | localhost 계열 | |
| PostgreSQL | `POSTGRES_DB` · `POSTGRES_USER` · `POSTGRES_PASSWORD` · `POSTGRES_HOST` · `POSTGRES_PORT` | `postgres:5432` | 비밀번호는 바꿔서 사용 |
| Celery | `CELERY_BROKER_URL` · `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` · `/1` | |
| | `CELERY_TASK_TIME_LIMIT` | 600 | soft limit 570 |
| AI 호출 | `AI_SERVICE_URL` · `AI_SERVICE_TIMEOUT` | `http://fastapi:8001` · 300 | 연결 5초 · 응답 300초 |
| 입력 | `MAX_UPLOAD_MB` · `LOW_CONFIDENCE_THRESHOLD` | 100 · 0.55 | |
| IP Webcam | `IP_WEBCAM_ALLOWED_URLS` | `http://PHONE_IP:8080/video` (쉼표로 여러 개) | 화면은 번호만 고름 · 주소는 응답 · 로그 · DB 에 남기지 않음 |
| | `CAMERA_CAPTURE_SECONDS` · `CAMERA_CONNECT_TIMEOUT` | 8 · 10 | |

`.env.example` 에 없고 코드 기본값으로 쓰는 값: `PENDING_STALE_MINUTES` 10 · `POLL_TIMEOUT_SECONDS` 600 · `CAMERA_PREVIEW_MAX_SECONDS` 60 · `MAX_VIDEO_SECONDS` 60 · `SERVE_MEDIA` False · `CELERY_TASK_ALWAYS_EAGER` False

Celery 등록이 Redis 장애에 오래 붙잡히지 않도록 정한 값 (`settings.py`)

```python
CELERY_BROKER_CONNECTION_TIMEOUT = 3
CELERY_TASK_PUBLISH_RETRY_POLICY = {"max_retries": 2, "interval_start": 0, "interval_step": 0.5, "interval_max": 1}
CELERY_REDIS_SOCKET_CONNECT_TIMEOUT = 3
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {...}   # 결과 저장소 재연결도 기본 20번 → 2번
```

## 4. 헬스체크

| 주소 | 확인하는 것 | 정상 | 실패 |
|---|---|---|---|
| `GET http://localhost:8000/api/v1/health/` | `SELECT 1` · Redis ping (2초) | 200 `{"status":"ok","checks":{"db":{"ok":true,"ms":0.7},"redis":{"ok":true,"ms":1.7}}}` | 503 `status: "error"` → compose `unhealthy` |
| `GET http://localhost:8001/health` | 모델 · Pose 로드 상태 | 200 `status: "ok"` · `n_features 1140` | 200 `status: "degraded"` + `error` |

## 5. 로그 읽기

```bash
docker compose logs -f django celery            # 작업 흐름
docker compose logs fastapi | grep -v /health   # 추론 (헬스체크 줄 제외)
docker compose logs celery | grep "job#35"      # 작업 하나만
```

모든 앱 로그는 `[2026-11-24 20:33:53 +0900] INFO analyses.tasks: …` 형식 (시간대가 보이게 `%z`) 입니다. **job 번호 하나로 세 서비스 로그를 잇습니다.**

| 서비스 | 로그 (코드) | 예 |
|---|---|---|
| django | `views.py:40` 등록 · `:112` 멈춘 작업 삭제 · 등록 실패 ERROR | `job#33 대기열 등록 task=b4bd2184-…` |
| celery | `tasks.py:104` 시작 · `:108` 영상 확보 · `:112` AI 응답 · `:116` 저장 · `:31` 실패 | `job#N 시작 input=UPLOAD … 대기열 대기 0.0s` → `영상 확보` → `AI 추론 응답 3.4s predictions=1` → `저장 완료 SUCCESS 총 3.5s` |
| fastapi | `predictions.py` (`X-Job-ID` 헤더) | `job#N wave.mp4: 126 frames, 1 tracks, 1 predictions, 3331 ms` |

celery · fastapi 예는 코드(`tasks.py` · `predictions.py`)의 로그 형식입니다. 실제 출력으로 남긴 개선 후 로그는 django 쪽([cb_1_django_log_v1.txt](evidence/logs/cb_1_django_log_v1.txt))이고, celery 단계 로그와 fastapi `job#N` 줄은 자동 테스트(`test_success_logs_each_step_with_job_id` · `test_services_sends_job_id_header`)로 확인했습니다.

개선 전에는 성공한 작업의 단계 로그가 없고 (F2), FastAPI 로그에 파일 이름만 있었고 (F3), fastapi 로그만 UTC 라 9시간이 어긋났습니다 (F7) → [improvements.md](improvements.md)

## 6. 시연 설정 (운영 전에 바꿀 것)

| 지금 | 이유 | 운영 |
|---|---|---|
| `DJANGO_DEBUG=True` | 개발 중 오류 확인 | `False` (500 이 디버그 페이지로 보이는 F9 해결) |
| `BasicAuthentication` 허용 | curl 로 API 확인 | 세션 · 토큰만 |
| Django 가 `/media/` 직접 제공 | nginx 없이 실행 | nginx · 오브젝트 스토리지 |
| gunicorn 접근 로그 없음 | 앱 로그 `job#N` 로 대신 | 필요하면 `--access-logfile -` |

## 7. 재시작 뒤

PC 재부팅 직후 첫 분석이 `AI 서버 오류(503): 모델이 준비되지 않았습니다` 로 실패하면 `docker compose restart fastapi` 후 다시 시도합니다 (Docker Desktop 이 WSL 폴더 연결 전에 fastapi 를 먼저 올린 경우 · [troubleshooting.md](troubleshooting.md)).
