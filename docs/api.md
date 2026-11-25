# API

> 기준 코드: `main` 40d3916 · 주소 파일 `config/urls.py` · `config/api_urls.py` · `analyses/api_urls.py` · `analyses/urls.py` · `accounts/urls.py` · `ai_service/main.py` · `ai_service/routers/predictions.py`
> 응답 예시는 [evidence/logs/](evidence/logs/) 의 실제 출력에서 가져왔습니다. `be_b2_*` · `be_b3_*` 는 **개선 전 기록(/api/v1 이전)** 이라 주소 접두사만 지금과 다릅니다.

## 공통 규칙

| 항목 | 값 |
|---|---|
| 접두사 | `/api/v1/` (`config/urls.py:9` 한 곳). 옛 주소 `/api/analyses/` · `/accounts/api/` 는 404 (`test_old_api_urls_removed`) |
| 인증 | `SessionAuthentication` → `BasicAuthentication` (curl 확인용, 시연 설정) |
| 권한 | `IsAuthenticated`. 로그인 안 하면 **403** `{"detail":"자격 인증 데이터가 제공되지 않았습니다."}` · `/api/v1/health/` 만 예외 |
| 조회 범위 | `AnalysisJob.objects.visible_to(user)` · 관리자 전체, 회원 본인 것만. **남의 작업 id 는 404** (있는지조차 숨김) |
| 페이지 | `PageNumberPagination` · 20개씩 · `{count, next, previous, results}` |
| CSRF | 세션 로그인 상태의 POST · PATCH · DELETE 는 `X-CSRFToken` 헤더 필요 (`analyses.js:18` 이 폼의 `csrfmiddlewaretoken` 값을 읽어 보냄) |
| 허용 안 하는 메서드 | `PUT` 405 (`http_method_names` 에서 제외) |

## 엔드포인트 한눈에

| 메서드 | 주소 | 처리 함수 | 응답 코드 |
|---|---|---|---|
| `GET` | `/api/v1/analyses/` | `AnalysisJobViewSet.list()` | 200 · 403 |
| `POST` | `/api/v1/analyses/` | `create()` · `AnalysisJobCreateSerializer` | **202** · 400 · 403 · 503 |
| `GET` | `/api/v1/analyses/{id}/` | `retrieve()` · `AnalysisJobSerializer` | 200 · 403 · 404 |
| `PATCH` | `/api/v1/analyses/{id}/` | `partial_update()` · `AnalysisJobUpdateSerializer` | 200 · 400 · 403 · 404 |
| `PUT` | `/api/v1/analyses/{id}/` | — | 405 |
| `DELETE` | `/api/v1/analyses/{id}/` | `destroy()` | 204 · 403 · 404 · 409 |
| `GET` | `/api/v1/analyses/{id}/status/` | `@action status()` · `AnalysisJobStatusSerializer` | 200 · 403 · 404 |
| `GET` | `/api/v1/auth/me/` | `accounts.views.me` · `MeSerializer` | 200 · 403 |
| `GET` | `/api/v1/health/` | `config.health.health` (로그인 불필요) | 200 · 503 · 405 |
| `GET` | `/cameras/{index}/stream/` | `stream_views.camera_stream` (화면용) | 200 MJPEG · 302 · 404 · 405 · 502 |
| `GET` | FastAPI `/health` | `ai_service/main.py health()` | 200 (`ok` / `degraded`) |
| `POST` | FastAPI `/predict/video` | `routers/predictions.py predict_video()` | 200 · 400 · 413 · 422 · 503 |

화면 주소 (`/` · `/analyses/{id}/` · `/dashboard/` · `/accounts/…` · `/admin/`) 는 [architecture.md](architecture.md) 와 아키텍처 그림 아래 주소 표에 있습니다.

## 분석 등록 `POST /api/v1/analyses/`

요청 (multipart/form-data)

| 필드 | 필수 | 설명 |
|---|---|---|
| `input_type` | ✔ | `UPLOAD` · `WEBCAM` |
| `video_file` | UPLOAD 일 때 | mp4 · mov · avi · mkv · 최대 `MAX_UPLOAD_MB`(100) |
| `camera_index` | WEBCAM 일 때 (기본 0) | `IP_WEBCAM_ALLOWED_URLS` 의 순번. 주소 자체는 받지도 저장하지도 않음 |
| `title` · `memo` | | 최대 100자 · 자유 |
| `expected_action` | | 6개 Label 중 하나. 사용자가 하려던 동작일 뿐 정답 Label 이 아님 |

```bash
curl -u <회원아이디>:<비밀번호> -F input_type=UPLOAD -F title="손 흔들기" -F video_file=@wave.mp4 \
     http://localhost:8000/api/v1/analyses/
```

응답

```json
202 Accepted
{"id": 12, "task_id": "8d2e6411-e56d-4427-b78a-3b619693976a", "status": "PENDING", "status_url": "/api/v1/analyses/12/status/"}
```

- `task_id` 는 Django 가 `uuid4()` 로 미리 만들어 DB `celery_task_id` 에 저장하고 Celery 에도 같은 값을 넘깁니다. 로그 · DB · Redis 를 이 값 하나로 잇습니다.
- `status_url` 은 `reverse("api:analysis-status")` 로 만듭니다 (주소 하드코딩 없음).
- 400: `{"video_file": ["지원하지 않는 형식입니다(.txt). 허용: mp4, mov, avi, mkv"]}` 처럼 필드별 오류. 작업 행을 만들기 전에 거절합니다.
- 503 (Redis 등록 실패): 작업은 FAILURE 로 남고 이유가 저장됩니다.

```json
503 Service Unavailable
{"id": 34, "task_id": "f34c11b5-…", "status": "FAILURE", "detail": "작업 대기열(Redis)에 등록하지 못했습니다. Redis와 Celery Worker 상태를 확인한 뒤 다시 시도하세요."}
```

## 상태 조회 `GET /api/v1/analyses/{id}/status/` (폴링용)

```json
200 OK
{"id": 35, "status": "SUCCESS", "status_display": "완료", "is_finished": true, "is_stale": false,
 "error_message": "", "result_message": "1명의 동작을 예측했습니다.",
 "celery_task_id": "337b58fc-…", "prediction_count": 1,
 "started_at": "2026-11-24T20:33:53.577796+09:00", "finished_at": "2026-11-24T20:33:58.091324+09:00"}
```

- `prediction_count` 는 `annotate(Count("predictions"))` 로 셉니다. 예측 행은 읽지 않습니다 (쿼리 4 → 3).
- `is_stale` 이 true 면 화면은 폴링을 멈추고 「작업이 멈춘 것 같습니다」 안내를 띄웁니다. 기준은 [data-model.md](data-model.md#상태와-멈춘-작업).
- 화면은 2초(`POLL_MS`)마다 부르고, `POLL_TIMEOUT_SECONDS`(600초)가 지나면 멈춥니다.

## 상세 `GET /api/v1/analyses/{id}/`

```json
200 OK
{"id": 12, "username": "user", "title": "B2 curl 등록", "memo": "", "input_type": "UPLOAD", "input_type_display": "영상 업로드",
 "video_url": "/media/videos/2026/11/24/wave.mp4", "camera_index": null, "capture_seconds": null, "expected_action": "",
 "status": "SUCCESS", "status_display": "완료", "celery_task_id": "8d2e6411-…", "error_message": "",
 "result_message": "1명의 동작을 예측했습니다.", "video_frames": 126, "video_fps": 25.0, "video_duration_sec": 5.04,
 "processing_ms": 3625, "total_seconds": 3.8,
 "created_at": "2026-11-24T11:50:45.600074+09:00", "started_at": "2026-11-24T11:50:45.700510+09:00", "finished_at": "2026-11-24T11:50:49.378153+09:00",
 "predictions": [{"id": 10, "track_id": 1, "action_label": "wave", "action_display": "A006 손 흔들기", "confidence": 0.4533,
   "is_uncertain": true, "window_count": 4, "frame_count": 126,
   "probabilities": {"wave": 0.4533, "sit_stand": 0.1117, "bend_return": 0.11, "drink_return": 0.1625, "walk_turn_walk": 0.0408, "leg_raise_lower": 0.1217},
   "created_at": "2026-11-24T11:50:49.376070+09:00"}]}
```

(`be_b2_curl_api.txt` · 개선 전 주소로 받은 응답입니다. 필드는 지금과 같습니다.)

- `is_uncertain` = `confidence < LOW_CONFIDENCE_THRESHOLD`(0.55). 화면은 이 값만 보고 「판단 불확실」을 표시합니다 (D2).
- 남의 작업: `404 {"detail": "No AnalysisJob matches the given query."}` (문구 그대로 둠 · F6)

## 수정 `PATCH` · 삭제 `DELETE`

| 요청 | 결과 | 이유 |
|---|---|---|
| `PATCH {"title": …, "memo": …}` | 200 · 상세 JSON | `AnalysisJobUpdateSerializer` 필드가 title · memo 뿐 |
| `PATCH {"status": "SUCCESS", "processing_ms": 1}` | 200 · **값 그대로** | 모르는 필드는 무시 → AI 결과를 API 로 바꿀 수 없음 |
| `PUT` | 405 | 전체 덮어쓰기 차단 |
| 처리 중 `DELETE` | 409 `{"detail": "분석이 진행 중인 작업은 삭제할 수 없습니다."}` | Worker 가 지워진 행을 찾다 실패하는 일을 막음 |
| 멈춘 작업 (`is_stale`) `DELETE` | 204 · 로그 `job#N 멈춘 작업(PENDING) 삭제` | 영구 PENDING 을 정리할 수 있게 함 |
| 끝난 작업 `DELETE` | 204 · 예측 CASCADE · 영상 파일도 삭제 | |

## 회원 · 헬스체크

```json
GET /api/v1/auth/me/  →  200 {"id": 2, "username": "user", "email": "", "is_staff": false, "date_joined": "…"}
GET /api/v1/health/   →  200 {"status": "ok", "checks": {"db": {"ok": true, "ms": 0.7}, "redis": {"ok": true, "ms": 1.7}}}
                         503 {"status": "error", "checks": {…, "redis": {"ok": false, …}}}
```

`/api/v1/health/` 는 `_check_db()` (`SELECT 1`) 와 `_check_redis()` (ping, 2초 제한) 를 부르고, compose `django` healthcheck 가 이 주소를 씁니다.

## 웹캠 미리보기 `GET /cameras/{index}/stream/`

| 경우 | 응답 |
|---|---|
| 허용 목록 카메라 · MJPEG | 200 `multipart/x-mixed-replace` · `Cache-Control: no-store` · `X-Accel-Buffering: no` · 최대 `CAMERA_PREVIEW_MAX_SECONDS`(60초) 뒤 서버가 끊음 |
| 로그인 안 함 | 302 → `/accounts/login/` |
| 목록 밖 번호 | 404 |
| GET 아님 | 405 |
| 카메라 꺼짐 · MJPEG 아님 | 502 `text/plain` (카메라 주소는 응답에 넣지 않음) |

증거: [images/stream_200_mjpeg.png](images/stream_200_mjpeg.png) · [images/stream_502_camera_off.png](images/stream_502_camera_off.png)

## FastAPI (내부 전용)

`127.0.0.1:8001` 에만 공개되고, Celery 는 compose 안에서 `http://fastapi:8001` 로 부릅니다.

`POST /predict/video` (multipart `file`, 헤더 `X-Job-ID` 선택)

```json
200 OK  (be_b3_fastapi.txt)
{"person_found": true, "message": "1명의 동작을 예측했습니다.", "processing_ms": 3248,
 "video": {"fps": 25.0, "frames": 126, "width": 640, "height": 480, "duration_sec": 5.04, "analyzed_frames": 126},
 "model": {"classes": ["bend_return", "drink_return", "leg_raise_lower", "sit_stand", "walk_turn_walk", "wave"],
           "n_features": 1140, "sequence_steps": 30, "window_seconds": 5.0, "confidence_threshold": 0.55},
 "predictions": [{"track_id": 1, "action_label": "wave", "confidence": 0.4533, "windows": 4, "frame_count": 126,
                  "mode": "window", "stable_label": "UNKNOWN", "probabilities": {"…": 0.0}}]}
```

| 코드 | 경우 | 실제 응답 (be_b3) |
|---|---|---|
| 400 | 확장자 · 빈 파일 | `지원하지 않는 영상 형식입니다(.txt).` · `빈 파일입니다.` |
| 413 | 크기 초과 | `파일이 너무 큽니다(…MB > 100MB).` |
| 422 | 영상을 못 읽음 · `file` 없음 | `영상을 열 수 없습니다(손상되었거나 지원하지 않는 코덱).` |
| 503 | 모델 로드 실패 | `모델이 준비되지 않았습니다: …` |

Celery 쪽 `services.predict_video()` 는 연결 실패 · 시간 초과 · 4xx / 5xx 를 모두 `AIServiceError` 로 바꾸고, `run_analysis` 가 FAILURE + 이유로 저장합니다.

`GET /health` → `{"status": "ok", "model_loaded": true, "classes": […6개], "n_features": 1140, "sequence_steps": 30, "feature_dim": 38, "pose_model": "yolo11n-pose.pt", "error": null}` · 모델이 없으면 `status: "degraded"` 와 `error` 문구 ([images/fastapi_health.png](images/fastapi_health.png))
