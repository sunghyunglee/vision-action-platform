# Evidence

프로그램을 직접 실행해서 남긴 증거(화면 캡처 · 로그 · DB 조회)입니다. 모두 2026-11-23 ~ 11-24 에 이 저장소 코드를 Docker Compose 로 실행해 얻었습니다.

공개 전 처리

- 로컬 계정 아이디는 `user` (일반 회원) · `admin` (관리자) 로 바꿨습니다. 비밀번호는 `****` 로 가렸습니다.
- 셸 프롬프트 · PC 이름 · 홈 경로를 지우고, 카메라 IP 는 `<카메라-IP>` 로 가렸습니다. 쿠키 값이 보이는 캡처는 넣지 않았습니다.
- 사람이 나오는 캡처는 얼굴을 모자이크했습니다.
- **개선 전 기록(/api/v1 이전)**: 2026-11-24 주소 정리(dce0e1c) 전에 찍은 로그는 파일 맨 위에 이 표시가 있습니다. 그때 API 주소는 `/api/analyses/` 였고 지금은 `/api/v1/analyses/` 입니다.

## T01 ~ T10

| 기능 | 화면 | 로그 | DB |
|---|---|---|---|
| T01 모델 불러오기 | [fastapi_health.png](../images/fastapi_health.png) | [fastapi_log.txt](logs/fastapi_log.txt) (6 classes · 1140 features · yolo11n-pose) | — |
| T02 영상 업로드 분석 | [screen_upload_success.png](../images/screen_upload_success.png) | [celery_log2.txt](logs/celery_log2.txt) (job 6 received → succeeded 3.3초) | [db_jobs.txt](logs/db_jobs.txt) |
| T03 IP Webcam 8초 수집 | [screen_webcam_result.png](../images/screen_webcam_result.png) | [celery_log.txt](logs/celery_log.txt) (8초 · 146 · 158 프레임) | [db_jobs.txt](logs/db_jobs.txt) |
| T04 사람(Track)별 결과 | [screen_two_people.png](../images/screen_two_people.png) | [t04_fastapi_db.txt](logs/t04_fastapi_db.txt) (30 frames · 2 tracks · 2 predictions) | 같은 파일 (job 9 → 2행) |
| T05 비동기 202 | [api_post_202.png](../images/api_post_202.png) · [api_status_polling.png](../images/api_status_polling.png) | [celery_log.txt](logs/celery_log.txt) | — |
| T06 영구 저장 | [screen_detail_reload.png](../images/screen_detail_reload.png) | — | [db_jobs.txt](logs/db_jobs.txt) · [be_b9_restart.txt](logs/be_b9_restart.txt) |
| T07 CRUD · 권한 | [api_other_user_404.png](../images/api_other_user_404.png) · [tests_51_pass.png](../images/tests_51_pass.png) | [be_b2_curl_api.txt](logs/be_b2_curl_api.txt) | — |
| T08 관리자 | [screen_dashboard.png](../images/screen_dashboard.png) · [admin_pending_jobs_f8.png](../images/admin_pending_jobs_f8.png) · [dashboard_user_denied.png](../images/dashboard_user_denied.png) | — | — |
| T09 예외 처리 | [screen_webcam_failure.png](../images/screen_webcam_failure.png) · [screen_bad_file.png](../images/screen_bad_file.png) | [celery_log2.txt](logs/celery_log2.txt) (job#7 연결 거부 → FAILURE) | [db_jobs.txt](logs/db_jobs.txt) (#2 FAILURE + error_message) |
| T10 Docker Compose | [screen_after_restart.png](../images/screen_after_restart.png) | [compose_ps.txt](logs/compose_ps.txt) · [compose_ps_v1.txt](logs/compose_ps_v1.txt) | [be_b9_restart.txt](logs/be_b9_restart.txt) |

## 로그 (`logs/`)

| 파일 | 내용 | 시점 |
|---|---|---|
| `be_b2_curl_api.txt` | B2 curl API 계약 (403 · 202 · 404 · 405 · 409 · 204) | 개선 전 |
| `be_b3_fastapi.txt` | B3 FastAPI 단독 (/health · 200 · 400 · 422) | 개선 전 |
| `be_b4_timeline.txt` | B4 job 12 세 서비스 로그 타임라인 | 개선 전 |
| `be_b5_db.txt` | B5 PostgreSQL 직접 조회 | 개선 전 |
| `be_b6_redis.txt` | B6 Redis db0 · db1 조회 | 개선 전 |
| `be_b7_fault.txt` | B7 Celery · FastAPI · Redis 정지 | 개선 전 |
| `be_b8_timing.txt` | B8 같은 영상 6회 처리 시간 | 개선 전 |
| `be_b9_restart.txt` | B9 재시작 전후 행 수 | 개선 전 |
| `be_f4_poll_v1.txt` | F4 개선 후: 멈춘 작업 `is_stale` → 폴링 멈춤 | 개선 후 |
| `be_f8_redis_v1.txt` | F8 개선 후: Redis 정지 → 16.1초 503 · FAILURE · 복구 뒤 SUCCESS | 개선 후 |
| `cb_1_django_log_v1.txt` | F1 · F7 개선 후: django `job#33 대기열 등록` · `+0900` | 개선 후 |
| `celery_log.txt` · `celery_log2.txt` | T03 · T05 · T02 · T09 Worker 로그 | 개선 전 |
| `compose_ps.txt` | 5개 서비스 상태 (django healthcheck 없음) | 개선 전 |
| `compose_ps_v1.txt` | 5개 서비스 상태 (django healthy) | 개선 후 |
| `db_jobs.txt` · `db_predictions.txt` | 작업 · 예측 테이블 | 개선 전 |
| `err_model_not_ready_20261124.txt` | 재부팅 뒤 AI 서버 503 · 해결 | 개선 전 |
| `fastapi_log.txt` · `fastapi_pose_conf_fix.txt` | 모델 로드 · Pose conf 0.50 → 0.25 | 개선 전 |
| `t04_fastapi_db.txt` | 두 사람 영상 · Track 2개 | 개선 전 |
| `tests_docker_20261124_fail.txt` · `_pass.txt` | 47개 중 9 ERROR → 수정 → 47 OK | 개선 후 |
| `tests_docker_dedupe_pass.txt` | 51 OK (중복 정리 후) | 개선 후 |
| `webcam_retry_compare.txt` | 웹캠 조건 바꿔 4회 · 모두 sit_stand | 개선 전 |

## 캡처 (`../images/`)

| 묶음 | 파일 |
|---|---|
| 작동 화면 | `screen_upload_success` · `screen_webcam_result` · `screen_webcam_failure` · `screen_two_people` · `screen_detail_reload` (얼굴 모자이크) · `screen_dashboard` · `screen_bad_file` · `screen_after_restart` · `screen_webcam_preview` (얼굴 모자이크) |
| API (새 주소) | `api_post_202` · `api_status_polling` · `api_list_json` · `api_health_200` · `api_other_user_404` · `fastapi_health` |
| 웹캠 미리보기 | `stream_200_mjpeg` · `stream_502_camera_off` |
| 권한 · 회원 | `dashboard_user_denied` · `logout_post_302` |
| 장애 기록 | `admin_pending_jobs_f8` (개선 전 Redis 장애로 남은 job 18 · 19) |
| 정리 후 | `after_index_job31` · `after_detail_job31` (얼굴 모자이크) · `after_dashboard` |
| 테스트 | `tests_51_pass` |
| README 합성 · 그림 | `screens` · `screens_2` · `evidence` · `backend_analysis` · `architecture` · `pipeline` (각각 `.en` 영어판) |
