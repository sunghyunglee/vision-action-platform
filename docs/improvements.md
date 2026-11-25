# Improvements

> 백엔드 분석([testing.md](testing.md))에서 찾은 문제를 **발견 → 원인 → 바꾼 것 → 확인** 순서로 정리했습니다. 개선 전 기준 9a01b0c → 개선 후 40d3916 (2026-11-24, 37개 파일).

## 1. 한눈에

| # | 발견 | 바꾼 것 | 커밋 | 확인 |
|---|---|---|---|---|
| 1 | `.env.example` 값이 실제와 다름 (Pose conf 0.50 · 판단 기준) | 원본 `person_confidence` 0.25 · `LOW_CONFIDENCE_THRESHOLD` 0.55 | 666417d | [fastapi_pose_conf_fix.txt](evidence/logs/fastapi_pose_conf_fix.txt) |
| 2 | API 가 `/api/` · `/accounts/api/` 로 흩어지고 JS 에 주소 하드코딩 | `/api/v1/` 한 곳 · `reverse()` · 템플릿이 JS 에 주소 전달 | dce0e1c | 테스트 4개 · [api_post_202.png](images/api_post_202.png) |
| 3 | django 컨테이너만 상태 확인 없음 | `GET /api/v1/health/` (DB · Redis) + compose healthcheck | eb45b88 | 테스트 3개 · [compose_ps_v1.txt](evidence/logs/compose_ps_v1.txt) |
| 4 | Redis 장애 시 105초 정체 · 500 · 영구 PENDING · 삭제 불가 (F8 · F5) | `enqueue_analysis()` · 짧은 재시도 · FAILURE + 503 · `is_stale` 삭제 허용 | aee65c9 | 테스트 5개 · [be_f8_redis_v1.txt](evidence/logs/be_f8_redis_v1.txt) |
| 5 | Worker 가 죽으면 화면이 끝없이 대기 (F4) | 폴링 최대 10분 · `is_stale` 이면 멈추고 안내 | eddadd8 | 테스트 1개 · [be_f4_poll_v1.txt](evidence/logs/be_f4_poll_v1.txt) |
| 6 | 성공 로그 없음 · FastAPI 에 job 번호 없음 · 시간대 9시간 차이 (F1 · F2 · F3 · F7) | `job#N` 단계 로그 · `X-Job-ID` · `TZ=Asia/Seoul` · `+0900` | 97fe7c1 | 테스트 3개 · [cb_1_django_log_v1.txt](evidence/logs/cb_1_django_log_v1.txt) |
| + | IP Webcam 은 찍히는 모습을 볼 수 없었음 | Django MJPEG 중계 `/cameras/<index>/stream/` (최대 60초) | f096d9b | 테스트 10개 · [screen_webcam_preview.png](images/screen_webcam_preview.png) |
| 최적화 | 권한 규칙 중복 · N+1 쿼리 · 죽은 코드 | 7개 커밋 (아래) | 40dd39c ~ 61e944d | 테스트 4개 |
| 정리 | 같은 HTML · 문구 · 집계가 여러 곳에 | D1 ~ D5 (아래) | b62f4bd ~ 40d3916 | 테스트 4개 |

## 2. 개선별 상세

### 개선 2 · API 주소 `/api/v1/`

- **원인**: 화면 · API 주소가 `analyses/urls.py` 한 파일에 섞이고, `analyses.js` 가 `/api/analyses/` 를 문자열로 들고 있었습니다.
- **바꾼 것**: `config/urls.py:9` `path("api/v1/", include("config.api_urls"))` → `config/api_urls.py` (`app_name = "api"`) 가 `analyses.api_urls` · `auth/me/` · `health/` 를 모읍니다. `create()` 는 `reverse("api:analysis-status")` 로 `status_url` 을 만들고, `index.html` 은 `data-list-url` 등으로 JS 에 주소를 넘깁니다.
- **확인**: `test_api_urls_are_versioned` · `test_old_api_urls_removed` (옛 주소 404) · `test_create_returns_status_url_from_reverse` · `test_index_passes_api_urls_to_js`

### 개선 4 · 등록 실패 처리 (가장 큰 개선)

```text
개선 전  POST ──▶ Job 커밋(PENDING) ──▶ on_commit: apply_async ──(Redis 없음, 재연결 반복 105.2초)──▶ 500 디버그 페이지
                                                                             └ Job 은 영원히 PENDING, DELETE 도 409
개선 후  POST ──▶ Job 커밋(PENDING) ──▶ on_commit: enqueue_analysis() ──(재시도 2회 · 연결 3초)──▶ 실패
                                         └ Job = FAILURE + "작업 대기열(Redis)에 등록하지 못했습니다 …" ──▶ 503 (16.1초)
```

- 설정: `CELERY_BROKER_CONNECTION_TIMEOUT 3` · `CELERY_TASK_PUBLISH_RETRY_POLICY max_retries 2` · 결과 저장소 재연결도 20번 → 2번
- 멈춘 작업: `AnalysisJob.is_stale` (PENDING 10분 · STARTED 제한 + 60초) 이면 `destroy()` 가 409 대신 삭제
- 확인: 테스트 `test_enqueue_failure_saved_as_failure` · `test_enqueue_failure_returns_503_outside_transaction` · `test_fresh_pending_cannot_be_deleted` · `test_stale_pending_can_be_deleted` · `test_stale_started_can_be_deleted` + 실제 Redis 정지 재측정 (job 34 FAILURE · 복구 뒤 job 35 SUCCESS)
- 남은 것: 실패 응답까지 16.1초가 걸립니다. 105.2초보다 크게 줄었지만 0 은 아니며, 16초의 내역은 따로 나눠 재지 않았습니다 (미확인).

### 개선 5 · 폴링 제한

- `analyses.js` `poll()` 은 2초(`POLL_MS`)마다 `status/` 를 부르고, `POLL_TIMEOUT_SECONDS`(600, 템플릿이 전달) 가 지나거나 응답의 `is_stale` 이 true 면 `stopPolling()` 후 「작업이 멈춘 것 같습니다(Worker가 가져가지 않음)…」 안내를 띄웁니다.
- 확인: `test_index_passes_poll_timeout_to_js` · 실제 PENDING 작업에서 폴링이 멈춤 ([be_f4_poll_v1.txt](evidence/logs/be_f4_poll_v1.txt))

### 개선 6 · 작업 로그

| 전 | 후 |
|---|---|
| 성공하면 Celery 의 `received` · `succeeded in Ns` 두 줄뿐 | `job#N 시작 … 대기열 대기` → `영상 확보` → `AI 추론 응답 … processing_ms` → `저장 완료 … 총` |
| FastAPI: `wave_xxxx.mp4: 126 frames …` 처럼 저장 파일 이름만 (업로드 작업은 시각으로 맞춰야 했음) | `job#N wave.mp4: …` (`services.py` 가 `X-Job-ID` 헤더를 보냄) |
| django 로그에 정상 요청 흔적 없음 | `job#33 대기열 등록 task=b4bd2184-…` |
| celery KST · fastapi UTC | 세 서비스 KST · 모든 줄에 `+0900` |

## 3. 최적화 (7개 커밋, 동작 변화 없음)

| 커밋 | 무엇 | 효과 |
|---|---|---|
| 40dd39c | API · 상세 화면이 각자 쓰던 권한 필터 → `AnalysisJob.objects.visible_to(user)` 하나 | 규칙이 한 곳 |
| 7ed3b3e | 상태 폴링 · Admin 목록의 예측 수를 `annotate(Count)` 로 (N+1 제거) | **Admin 목록 27 → 7 쿼리 · 상태 조회 4 → 3 쿼리** |
| b12af91 | 쓰지 않는 `services.check_health` · `ASGI_APPLICATION` 삭제 | |
| 11ced83 | 폴링 종료 처리 중복 → `stopPolling()` 하나 | |
| 4837b68 | `ai_service/src` 에서 서버가 쓰지 않는 함수 삭제 (Feature 계산 중복 3곳 → 1곳) | **692줄 삭제** |
| 17acaec | `pose_pipeline` 의 `MODEL_DIR` 중복 정의 제거 | |
| 61e944d | ai_service 의존성에서 pandas 제거 | 쓰지 않는 의존성 정리 |

확인: `test_visible_to` · `test_detail_page_and_api_follow_same_rule` · `test_status_poll_counts_without_loading_predictions` · `test_admin_changelist_does_not_grow_with_rows` (행이 늘어도 쿼리 수 그대로)

## 4. 중복 정리 D1 ~ D5

| # | 커밋 | 전 | 후 | 테스트 |
|---|---|---|---|---|
| D4 | b62f4bd | 상태 배지 HTML 이 분석 · 상세 · 대시보드에 따로 | `_status_badge.html` 하나 | `test_status_badge_same_on_three_pages` |
| D1 | 1d03032 | 분석 직후 JS 가 만든 이력 줄은 배지 모양이 달랐음 | 서버 이력과 같은 배지 | (같은 테스트 · [after_index_job31.png](images/after_index_job31.png)) |
| D2 | 3b055ff | 화면이 0.55 기준값을 따로 받아 다시 비교 | API 의 `is_uncertain` 만 사용 | `test_uncertain_comes_from_api_not_page` |
| D3 | ef41471 | 카메라 연결 실패 문구가 수집 · 미리보기에 따로 | `CAMERA_CONNECT_FAILED` 하나 | `test_camera_message_shared` |
| D5 | d0a3847 | 대시보드 집계 코드 반복 · 안 쓰는 `import json` | `_count_by()` 하나 | `test_count_by` |

정리 뒤 화면: [after_index_job31.png](images/after_index_job31.png) · [after_detail_job31.png](images/after_detail_job31.png) · [after_dashboard.png](images/after_dashboard.png) (작업 28 · 예측 26)

## 5. 그대로 둔 것

| 항목 | 이유 |
|---|---|
| F6 404 문구의 모델 이름 | DRF 기본 동작 · 보안 영향 작음 |
| F9 · `DEBUG=True` · BasicAuth · Django 가 `/media/` 제공 | 시연 설정. 운영 전환 목록은 [operations.md](operations.md#6-시연-설정-운영-전에-바꿀-것) |
| 모델 정확도 | 학습 데이터 한계 → [ai-inference.md](ai-inference.md#6-데이터-한계-정확도를-올릴-수-없는-이유) |
| 개선 후 처리 시간 재측정 | 하지 않았음 (미확인). 아키텍처가 그대로라 B8 값을 기준으로 둠 |
