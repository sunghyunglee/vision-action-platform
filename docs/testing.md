# Testing · Backend Analysis

> 자동 테스트 51개 (40d3916) + 직접 실행한 백엔드 분석 B1 ~ B10 · 원본 출력은 [evidence/logs/](evidence/logs/)
> B2 ~ B9 는 **개선 전 기록(/api/v1 이전)** 입니다. 주소 접두사만 다르고, 개선 뒤 다시 확인한 항목은 따로 적었습니다.

## 1. 자동 테스트 51개

```bash
docker compose exec django python manage.py test     # Ran 51 tests · OK (PostgreSQL)
```

- Celery 는 `CELERY_TASK_ALWAYS_EAGER` 로 바로 실행하고, `services.predict_video` · `capture_clip` · `requests.get` · Redis 확인은 mock 으로 바꿉니다. FastAPI · 카메라 없이 Django 쪽 흐름 전체를 검사합니다.
- 증거: [images/tests_51_pass.png](images/tests_51_pass.png) · [evidence/logs/tests_docker_dedupe_pass.txt](evidence/logs/tests_docker_dedupe_pass.txt) (2026-11-24 20:05 · 51 OK)

| 파일 | 개수 | 묶음 | 테스트 |
|---|---|---|---|
| `analyses/tests.py` | 36 | 등록 · 검사 | `test_create_returns_job_id_and_saves_predictions` · `test_create_requires_file_for_upload` · `test_rejects_wrong_extension` · `test_rejects_camera_not_in_allow_list` |
| | | 실패 처리 | `test_ai_failure_saved` · `test_camera_failure_saved` · `test_unknown_label_is_failure` |
| | | 권한 · 수정 · 삭제 | `test_other_user_cannot_access` · `test_patch_only_title_memo` · `test_delete_policy` · `test_admin_sees_all_and_dashboard` · `test_index_page_renders` |
| | | 개선 2 · /api/v1 | `test_api_urls_are_versioned` · `test_old_api_urls_removed` · `test_create_returns_status_url_from_reverse` · `test_index_passes_api_urls_to_js` |
| | | 개선 3 · 헬스체크 | `test_health_ok` · `test_health_redis_down_is_503` · `test_health_post_not_allowed` |
| | | 개선 4 · 등록 실패 · 멈춘 작업 | `test_enqueue_failure_saved_as_failure` · `test_enqueue_failure_returns_503_outside_transaction` · `test_fresh_pending_cannot_be_deleted` · `test_stale_pending_can_be_deleted` · `test_stale_started_can_be_deleted` |
| | | 개선 5 · 폴링 제한 | `test_index_passes_poll_timeout_to_js` |
| | | 개선 6 · 작업 로그 | `test_success_logs_each_step_with_job_id` · `test_failure_logs_total_time` · `test_services_sends_job_id_header` |
| | | 최적화 | `test_visible_to` · `test_detail_page_and_api_follow_same_rule` · `test_status_poll_counts_without_loading_predictions` · `test_admin_changelist_does_not_grow_with_rows` |
| | | 중복 정리 D1 ~ D5 | `test_status_badge_same_on_three_pages` · `test_uncertain_comes_from_api_not_page` · `test_camera_message_shared` · `test_count_by` |
| `analyses/test_camera_preview.py` | 10 | 웹캠 미리보기 | `test_url` · `test_login_required` · `test_camera_not_in_allow_list_404` · `test_relays_mjpeg_and_closes_camera` · `test_stops_after_max_seconds` · `test_browser_disconnect_closes_camera` · `test_camera_down_502_without_address` · `test_not_mjpeg_502` · `test_index_has_preview_without_camera_address` · `test_no_preview_without_cameras` |
| `accounts/tests.py` | 5 | 회원 | `test_signup_creates_user_and_logs_in` · `test_login_and_logout` · `test_anonymous_redirected_from_index` · `test_anonymous_api_denied` · `test_me_api` |

테스트 수 변화: 47 (웹캠 미리보기 · 최적화까지) → 51 (중복 정리 D1 ~ D5 테스트 4개 추가)

한 번 실패한 기록: 2026-11-24 15:51 Docker(PostgreSQL) 에서 47개 중 9개 ERROR (`test_camera_preview` · 테스트의 `res.close()` 가 테스트 DB 연결까지 닫음) → 6521481 에서 수정 → 16:06 47개 통과. [tests_docker_20261124_fail.txt](evidence/logs/tests_docker_20261124_fail.txt) · [_pass.txt](evidence/logs/tests_docker_20261124_pass.txt)

## 2. 기능 확인 T01 ~ T10

화면 · DB · 로그로 직접 확인한 10개 기능입니다. 증거 목록은 [evidence/README.md](evidence/README.md#t01--t10).

## 3. 백엔드 분석 B1 ~ B10

"설계대로 도는가"를 화면이 아니라 curl · 로그 · DB · Redis · 장애 주입으로 확인했습니다 (2026-11-24, 개선 전 코드 9a01b0c).

| 단계 | 무엇을 | 핵심 결과 | 원본 |
|---|---|---|---|
| B1 | 코드로 요청 흐름 20단계 추적 | 찾은 점 F1 ~ F5 | (코드 읽기) |
| B2 | curl 로 API 계약 9개 규칙 | 아래 표 | [be_b2_curl_api.txt](evidence/logs/be_b2_curl_api.txt) |
| B3 | FastAPI 단독 호출 | `/health` 200 · 정상 영상 200 3.251초 (처리 3,248 ms) · 손상 422 · 빈 파일 400 · `.txt` 400 · 파일 없음 422 | [be_b3_fastapi.txt](evidence/logs/be_b3_fastapi.txt) |
| B4 | task ID 하나로 세 서비스 로그 + DB 시각 잇기 | 합계 3.78초 = 대기열 0.027 · Worker 준비 0.11 · **추론 3.625 (96%)** · 저장 0.02 | [be_b4_timeline.txt](evidence/logs/be_b4_timeline.txt) |
| B5 | PostgreSQL 직접 조회 | 작업 12행 (SUCCESS 9 · FAILURE 3) · 예측 10행 · 두 사람 영상 job 9 = 2행 · 같은 영상 confidence 0.4533 반복 | [be_b5_db.txt](evidence/logs/be_b5_db.txt) |
| B6 | Redis 직접 조회 | db0 대기 0 (`LLEN celery` 0) · db1 결과 키 14개 TTL 1일 · 값은 `{job_id, status}` 만 | [be_b6_redis.txt](evidence/logs/be_b6_redis.txt) |
| B7 | 서비스 하나씩 끄기 | 아래 표 · F8 · F9 발견 | [be_b7_fault.txt](evidence/logs/be_b7_fault.txt) |
| B8 | 같은 영상 6회 처리 시간 | p50 3,331 ms (±0.8%) · 99.3% 가 추론 · 워밍업 +39% | [be_b8_timing.txt](evidence/logs/be_b8_timing.txt) |
| B9 | `docker compose restart` 전후 | 작업 22 · 예측 17 · 회원 2 그대로 | [be_b9_restart.txt](evidence/logs/be_b9_restart.txt) |
| B10 | 정리 | 찾은 점 F1 ~ F9 → 개선 목록 | 이 문서 · [improvements.md](improvements.md) |

### B2 API 계약 (개선 전 주소 `/api/analyses/`)

| 요청 | 결과 | 의미 |
|---|---|---|
| 로그인 없이 목록 | **403** | `IsAuthenticated` 가 view 전에 차단 |
| 영상 등록 | **202** · 0.181초 | 추론을 기다리지 않음 |
| 상태 · 상세 | 200 | |
| 남의 작업 | **404** | 존재 여부를 숨김 |
| `PATCH status · processing_ms` | 200 · 값 그대로 | 결과 조작 불가 |
| `PUT` | **405** | |
| 처리 중 `DELETE` | **409** | |
| 끝난 뒤 `DELETE` → 다시 조회 | **204** → 404 | 예측 CASCADE |

개선 뒤 새 주소로 다시 찍은 화면: [images/api_post_202.png](images/api_post_202.png) · [api_status_polling.png](images/api_status_polling.png) · [api_other_user_404.png](images/api_other_user_404.png) · [api_health_200.png](images/api_health_200.png)

### B7 장애 주입

| 끈 서비스 | 개선 전 | 개선 후 |
|---|---|---|
| Celery Worker | 202 즉시 · job 16 PENDING 유지 → Worker 다시 켜자 **SUCCESS** (Redis 가 메시지를 보관, 유실 0) · 그동안 화면은 끝없이 대기 (F4) | 10분 지나면 `is_stale` → 폴링 멈춤 · 안내 ([be_f4_poll_v1.txt](evidence/logs/be_f4_poll_v1.txt)) |
| FastAPI | 202 즉시 · job 17 **4.0초 만에 FAILURE** + 「AI 서버(FastAPI)에 연결할 수 없습니다」 | 그대로 (설계대로) |
| Redis | **105.2초** 응답 없음 → 500 (디버그 페이지, F9) · job 18 · 19 **영구 PENDING** · 삭제도 409 (F8 · F5) | **16.1초 → 503** · job 34 바로 FAILURE + 이유 · Redis 복구 뒤 새 등록 202 0.13초 → SUCCESS ([be_f8_redis_v1.txt](evidence/logs/be_f8_redis_v1.txt)) |

개선 전 영구 PENDING 으로 남은 job 18 · 19 는 Admin 에서 그대로 보존했습니다: [images/admin_pending_jobs_f8.png](images/admin_pending_jobs_f8.png)

## 4. 찾은 점 F1 ~ F9

| # | 찾은 점 | 확인 | 처리 |
|---|---|---|---|
| F1 | 정상 202 요청이 django 로그에 한 줄도 없음 (gunicorn 접근 로그 꺼짐) | B4 | 앱 로그 `job#N 대기열 등록 task=…` 추가 ([cb_1_django_log_v1.txt](evidence/logs/cb_1_django_log_v1.txt)) |
| F2 | 성공한 작업은 Worker 단계 로그 없음 | B4 | 시작 · 영상 확보 · 추론 · 저장 시간 로그 |
| F3 | FastAPI 로그에 job 번호 없이 파일 이름만 | B4 | `X-Job-ID` 헤더 |
| F4 | 폴링에 끝나는 시간이 없음 | B7a | `POLL_TIMEOUT_SECONDS` 600 · `is_stale` |
| F5 | Redis 가 꺼지면 커밋된 PENDING 이 영원히 남음 | B7c | 등록 실패 → FAILURE 저장 |
| F6 | 404 문구에 모델 이름 `AnalysisJob` | B2 | 영향 작아 그대로 (선택) |
| F7 | celery 는 KST, fastapi 는 UTC → 9시간 차이 | B4 | `TZ=Asia/Seoul` · 로그에 `+0900` |
| F8 | Redis 가 꺼지면 등록이 105초 붙잡힌 뒤 500 (gunicorn worker 3개 중 1개 점유) | B7c | 재시도 2회 · 연결 3초 · 503 |
| F9 | 500 이 Django 디버그 페이지로 나감 | B7c | 시연 설정이라 그대로 · 운영은 `DEBUG=False` |
