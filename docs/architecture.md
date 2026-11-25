# Architecture

> 기준 코드: `main` 40d3916 · 줄 번호는 이 커밋 기준입니다.
> 그림: [images/architecture.png](images/architecture.png) (English: [architecture.en.png](images/architecture.en.png)) · 생성기 [diagrams/make_architecture.py](diagrams/make_architecture.py)

## 1. 서비스 구성

| 서비스 (compose) | 이미지 · 실행 | 맡은 일 | 포트 |
|---|---|---|---|
| `django` | `./backend` · `migrate` → `gunicorn config.wsgi --workers 3 --timeout 120` | 화면 · DRF API · 입력 검사 · 작업 저장 · 큐 등록 · MJPEG 중계 | `8000:8000` |
| `celery` | `./backend` (같은 이미지) · `celery -A config worker --concurrency=2` | 영상 확보(업로드 경로 / IP Webcam 8초 수집) · FastAPI 호출 · 결과 저장 | 공개 안 함 |
| `fastapi` | `./ai_service` · `uvicorn main:app --port 8001` | 영상 → YOLO Pose · ByteTrack → 38-D → 30 Step → RandomForest → JSON. **DB 접근 없음** | `127.0.0.1:8001:8001` |
| `redis` | `redis:7-alpine` | Celery 브로커 db0 · 결과 백엔드 db1 | 공개 안 함 |
| `postgres` | `postgres:16-alpine` | `auth_user` · `analyses_analysisjob` · `analyses_personprediction` | 공개 안 함 |

설계 원칙

- **웹 응답과 추론을 분리**합니다. Django 는 작업을 PENDING 으로 저장하고 202 를 바로 돌려줍니다. 3 ~ 5초 걸리는 추론은 Celery 가 따로 맡습니다.
- **상태와 AI 결과는 Worker 만 씁니다.** API 로는 제목 · 메모만 고칠 수 있습니다 (`AnalysisJobUpdateSerializer`).
- **FastAPI 는 DB 를 모릅니다.** 영상 파일을 받아 JSON 만 돌려주므로, 모델을 바꿔도 Django 쪽 코드는 그대로입니다.
- **업무 데이터는 PostgreSQL 에만** 있습니다. Redis 결과 키에는 `{job_id, status}` 만 남고 1일 뒤 삭제됩니다.

## 2. 다이어그램 표기

- 위 줄 ① → ⑧: 분석 요청이 AI 까지 가는 길 (브라우저 → Django · DRF → Redis → Celery → FastAPI → YOLO Pose → 38-D → RandomForest)
- 아래 줄 ⑨ → ⑫: 결과가 저장되고 화면으로 돌아오는 길 (Celery 저장 → PostgreSQL → DRF 조회 → 브라우저)
- 화살표 위 글자 = 코드 호출과 데이터 형식, 파란 점선 = Django ORM 이 PostgreSQL 에 쓰는 지점 (INSERT PENDING · UPDATE STARTED / FAILURE)
- 그림 아래 **버튼 흐름** 칸 = 「AI 분석 시작」 한 번이 지나는 `파일:줄 → 함수` 21칸, **주소 표** = 모든 엔드포인트

## 3. 기능별 호출 흐름

### 3-1. 「AI 분석 시작」 (노드 ① ~ ⑫ 전부)

| # | 노드 | 파일 : 줄 | 함수 · 코드 | 하는 일 |
|---|---|---|---|---|
| 1 | ① | `backend/templates/analyses/index.html:65` | `<button id="start-btn" type="submit">` | `form#analysis-form`(:16) 전송 |
| 2 | ① | `backend/static/js/analyses.js:86` · `:88` | `submit` 핸들러 → `new FormData(form)` | 입력 방식 · 파일 · 카메라 번호 · 제목 · 메모 |
| 3 | ① | `analyses.js:100` | `fetch(urls.list, {method: "POST"})` | 주소는 `index.html` 의 `data-list-url`(`{% url 'api:analysis-list' %}`)에서 읽음 · `X-CSRFToken` |
| 4 | ② | `backend/config/urls.py:9` | `path("api/v1/", include("config.api_urls"))` | API 접두사는 여기 한 곳 |
| 5 | ② | `backend/config/api_urls.py:16` | `include("analyses.api_urls")` | `app_name = "api"` |
| 6 | ② | `backend/analyses/api_urls.py:12` | `router.register("analyses", AnalysisJobViewSet)` | DefaultRouter |
| 7 | ② | `backend/analyses/views.py:71` | `AnalysisJobViewSet.create()` | `SessionAuthentication` · `IsAuthenticated` 통과 후 실행 |
| 8 | ② | `backend/analyses/serializers.py:47` · `:57` · `:67` | `AnalysisJobCreateSerializer` · `validate_video_file()` · `validate()` | 확장자 mp4 / mov / avi / mkv · 100MB · WEBCAM 은 허용 목록 번호만 |
| 9 | ⑩ | `views.py:75` · `:76` | `uuid4()` → `serializer.save(user=…, celery_task_id=…)` | `AnalysisJob` INSERT · PENDING |
| 10 | ③ | `views.py:79` → `:36` · `:39` | `transaction.on_commit(enqueue_analysis)` → `run_analysis.apply_async([pk], task_id=…)` | 커밋 뒤 등록 · 실패하면 FAILURE 저장 후 503 (`:86`) |
| 11 | ② | `views.py:96` | `Response(…, status=202)` | `{id, task_id, status, status_url}` |
| 12 | ④ | `backend/analyses/tasks.py:88` | `run_analysis(job_id)` | Redis 에서 꺼냄 → STARTED 저장 |
| 13 | ④ | `tasks.py:106` → `:34` (`:44`) | `_prepare_video(job)` (WEBCAM 이면 `camera_capture.capture_clip()`) | 업로드 경로 또는 8초 · 30fps 수집 mp4 |
| 14 | ④ | `tasks.py:110` → `backend/analyses/services.py:19` · `:26` | `predict_video(path, job_id)` → `requests.post` | `X-Job-ID` 헤더 · timeout (5, 300) |
| 15 | ⑤ | `ai_service/routers/predictions.py:32-33` | `POST /predict/video` · `predict_video(request, file)` | 503 모델 미준비 · 400 확장자 · 빈 파일 · 413 크기 검사 → 임시 파일 |
| 16 | ⑥ | `predictions.py:56` → `ai_service/services/pose_pipeline.py:72` · `:82` | `run_in_threadpool(PosePipeline.process_video)` · `model.track()` | 사람 찾기 · ByteTrack · 관절 17개 |
| 17 | ⑦ | `pose_pipeline.py:100` → `ai_service/src/multi_person_utils.py:11` | `feature_from_keypoints(kp)` | 사람마다 38-D (34 + 각도 4) |
| 18 | ⑧ | `predictions.py:59` → `ai_service/services/action_inference.py:60` | `predict_tracks(action_model, tracks, cfg)` | 30 Step 보간 → 1,140 → `predict_proba` → 평균 → argmax |
| 19 | ⑨ | `tasks.py:50` · `:58` · `:60` | `save_result(job, data)` · `transaction.atomic()` · `bulk_create()` | Label 6개 확인 · 예측 저장 · SUCCESS |
| 20 | ⑪ | `analyses.js:128` · `:139` → `views.py:118-119` | `poll()` → `GET …/status/` → `@action status()` | 2초마다 · 예측 수는 `Count` 만 |
| 21 | ⑫ | `analyses.js:162` | `showResult()` → 결과 표 · `#detail-link`(index.html:81) | `is_uncertain` 이면 「판단 불확실」 |

### 3-2. 기타 화면 기능

| 기능 | 호출 흐름 (파일 : 줄) | 노드 |
|---|---|---|
| 탭 「영상 업로드 / IP Webcam」 | `index.html:11` · `:12` → `analyses.js` 가 입력 칸만 전환 (서버 요청 없음) | ① |
| 「미리보기 켜기」 | `index.html:46` → `analyses.js:42` · `:46` `img.src` → `analyses/urls.py:12` → `stream_views.py:55-57` `camera_stream()` (`@login_required` · `@require_GET`) → `:59` `get_allowed_camera_url()` → `:65` `requests.get` → `:78` `StreamingHttpResponse` (최대 60초) | ① → 휴대폰 |
| 「상세 결과 보기」 · 이력 링크 | `index.html:81` → `analyses/urls.py:10` → `page_views.py:27-28` `detail()` → `models.py:28` `visible_to()` → `detail.html` | ① → ⑪ → ⑩ → ⑫ |
| 「대시보드」 (관리자) | `base.html:17` → `analyses/urls.py:11` → `page_views.py:38-39` `dashboard()` (`@staff_member_required`) → `:33` `_count_by()` ORM 집계 → Chart.js | ① → 관리자 칸 → ⑩ |
| 가입 · 로그인 · 로그아웃 | `accounts/urls.py:7` · `:8` · `:9` → `accounts/views.py:11` `signup()` · `LoginView` · `LogoutView` (POST 만, `base.html:21`) | ① → ② → ⑩ (`auth_user` · `django_session`) |
| 「Admin」 | `base.html:18` → `config/urls.py:7` `admin.site.urls` → `analyses/admin.py` | ① → ② → ⑩ |

## 4. 아키텍처 ↔ 코드 대조표

그림의 노드 · 화살표 · 파일 · 함수 · 주소를 40d3916 코드와 하나씩 맞춰 본 결과입니다.

### 4-1. 노드

| 노드 | 그림 표기 | 코드 위치 (40d3916) | 결과 |
|---|---|---|---|
| ① 브라우저 | `index.html` · `analyses.js` | `templates/analyses/index.html` · `static/js/analyses.js` | 일치 |
| ② Django · DRF | `views.AnalysisJobViewSet.create()` | `analyses/views.py:71` | 일치 |
| ③ Redis | `redis://redis:6379/0` · 메시지 `run_analysis` | `.env.example` `CELERY_BROKER_URL` · `views.py:39` | 일치 |
| ④ Celery Worker | `tasks.run_analysis()` | `analyses/tasks.py:87-88` | 일치 |
| ⑤ FastAPI | `routers/predictions.py` `predict_video()` | `ai_service/routers/predictions.py:32-33` | 일치 |
| ⑥ YOLO Pose | `PosePipeline.process_video()` | `ai_service/services/pose_pipeline.py:72` | 일치 |
| ⑦ 38-D → 1,140 | `feature_from_keypoints()` | `ai_service/src/multi_person_utils.py:11` | 일치 |
| ⑧ RandomForest | `predict_tracks()` | `ai_service/services/action_inference.py:60` | 일치 |
| ⑨ Celery 저장 | `save_result()` · `bulk_create` | `tasks.py:50` · `:60` | 일치 |
| ⑩ PostgreSQL 16 | `AnalysisJob` · `PersonPrediction` | `analyses/models.py:33` · `:115` | 일치 |
| ⑪ Django · DRF 조회 | `visible_to(user)` · `status()` | `models.py:28` · `views.py:54` · `:119` | 일치 |
| ⑫ 브라우저 결과 | `poll()` · `showResult()` | `analyses.js:128` · `:162` | 일치 |
| 관리자 칸 | `dashboard()` · `_count_by()` · Admin | `page_views.py:33` · `:39` · `analyses/admin.py` | 일치 |
| 웹캠 미리보기 칸 | `/cameras/<index>/stream/` · 60초 | `analyses/urls.py:12` · `stream_views.py:57` · `settings.CAMERA_PREVIEW_MAX_SECONDS` | 일치 |
| 회원 칸 | signup · login · logout · `/api/v1/auth/me/` | `accounts/urls.py:7-9` · `config/api_urls.py:17` · `accounts/views.py:28` | 일치 |
| 헬스체크 칸 | `/api/v1/health/` · `_check_db` · `_check_redis` | `config/api_urls.py:18` · `config/health.py:18` · `:24` · `:33` | 일치 |

### 4-2. 화살표 (데이터 형식)

| 화살표 | 그림 표기 | 코드 근거 | 결과 |
|---|---|---|---|
| ① → ② | `POST /api/v1/analyses/` · FormData · ← 202 JSON | `analyses.js:88` · `:100` · `views.py:96` | 일치 |
| ② → ③ | `apply_async([pk], task_id)` · 커밋 뒤 | `views.py:39` · `:79` | 일치 |
| ③ → ④ | `run_analysis(job_id)` | `tasks.py:88` | 일치 |
| ④ → ⑤ | `POST /predict/video` · multipart mp4 | `services.py:21` · `:26` | 일치 |
| ⑤ → ⑥ | `process_video(tmp.name)` | `predictions.py:56` | 일치 |
| ⑥ → ⑦ | `keypoints.xy` (사람, 17, 2) | `pose_pipeline.py:100` | 일치 |
| ⑦ → ⑧ | ndarray (1, 1140) | `action_inference.py` `flatten_sequence(seq).reshape(1, -1)` | 일치 |
| ⑧ → ⑨ | 200 JSON `{person_found, message, processing_ms, video, model, predictions}` | `predictions.py` return | 일치 |
| ⑨ → ⑩ | `bulk_create` + `job.save()` | `tasks.py:60` | 일치 |
| ⑩ → ⑪ | `visible_to(user)` | `views.py:54` | 일치 |
| ⑪ → ⑫ | 상태 JSON · 결과 JSON · 2초 폴링 · 최대 10분 | `analyses.js:7` `POLL_MS` · `settings.POLL_TIMEOUT_SECONDS=600` | 일치 |

### 4-3. 다이어그램 변경 이력 (v4 → v5)

| 무엇 | 전 | 후 |
|---|---|---|
| 노드 이름 | 기술 이름만 | 기술 이름 + 역할 + 실제 파일 · 함수 |
| URL 경로 | `config/urls.py` 만 | `config/urls.py` → `config/api_urls.py` → `analyses/api_urls.py` 3단계 |
| 빠진 기능 | 웹캠 미리보기 · 헬스체크 · 회원 · `capture_clip` · 작업 로그 없음 | 옆 칸으로 추가 |
| 설정 파일 | 없음 | `project.json` · `models/` 3개 · `.env` · `compose.yaml` 읽는 지점 |
| 코드에 없는 것 | CSV 표시 | 삭제 (코드에 CSV 없음) |
| 버튼 흐름 | 없음 | 그림 아래 21칸 `파일:줄 → 함수` + 다른 버튼 6줄 |
| 주소 표 | 없음 | 18개 엔드포인트 · 메서드 · 처리 함수 · 응답 코드 · 지나는 노드 |

참고: `retrieve()` · `list()` 는 `ModelViewSet` 이 물려준 DRF 기본 메서드라 `views.py` 에 따로 정의돼 있지 않습니다 (`get_queryset()` `:54` 만 다시 씀).

## 5. 파이프라인 다이어그램

[images/pipeline.png](images/pipeline.png) 는 같은 기준으로 **파일 단위**를 그립니다: ① 설정 파일 (`project.json` · `models/` · `.env` · `compose.yaml`) → ② 서버 시작 (`lifespan` · `load_action_model` · `PosePipeline`) → ③ 입력 (URL · `analyses.js` · serializer · `create` · Redis · `_prepare_video`) → ④ 추론 → ⑤ 저장 · 표시 → ⑥ 검증 (테스트 3개 파일). 위 대조표와 같은 파일 · 함수 이름을 쓰고, 생성기 안의 함수 이름이 코드에 있는지 스크립트로 다시 확인했습니다.
