# Troubleshooting

개발 · 실행 중 실제로 겪은 문제와 해결 기록입니다. 근거 로그는 [evidence/logs/](evidence/logs/) 에 있습니다.

| 증상 | 원인 | 해결 | 확인 · 근거 |
|---|---|---|---|
| PC 재부팅 직후 첫 분석이 `AI 서버 오류(503): 모델이 준비되지 않았습니다: 모델 파일이 없습니다: /app/models/…` 로 FAILURE | Docker Desktop 이 WSL 폴더(bind mount) 연결 전에 fastapi 컨테이너를 먼저 올려 빈 `/app/models` 를 읽음 (추정) · PC 의 `ai_service/models` 에는 파일 4개가 그대로 있었음 | `docker compose restart fastapi` | 재시작 뒤 `/health` `status: ok` · 다음 작업 SUCCESS · 서버는 죽지 않고 작업만 FAILURE + 이유로 남음 ([err_model_not_ready_20261124.txt](evidence/logs/err_model_not_ready_20261124.txt)) |
| 사람이 보이는데도 검출이 적음 · FastAPI 로그 `conf=0.50` | `.env` 의 `POSE_CONF` 가 학습 프로젝트 원본 `person_confidence` 0.25 와 달랐음 | `.env.example` 을 원본 값으로 맞춤 (666417d) · fastapi 다시 생성 | 로그 `Pose 모델 로드: yolo11n-pose.pt (imgsz=640, conf=0.25, …)` ([fastapi_pose_conf_fix.txt](evidence/logs/fastapi_pose_conf_fix.txt)) |
| 분석이 「대기」에서 넘어가지 않음 | 다른 프로젝트의 Celery 컨테이너가 같은 Redis 6379 를 보고 있어 작업 메시지를 먼저 가져감 | `docker ps` 로 확인 후 그 컨테이너 `docker stop` · 이 프로젝트는 compose 내부 Redis 만 씀 (포트 공개 안 함) | 정지 뒤 새 작업 SUCCESS |
| 8001 포트 사용 중 | Docker 실행과 로컬 `uvicorn` 실행을 동시에 함 | 한쪽만 실행 · `ss -ltnp` 로 확인 | |
| Redis 가 꺼지면 「AI 분석 시작」이 2분 가까이 멈춘 뒤 500 | 커밋 뒤 `apply_async` 가 브로커 재연결을 오래 재시도 (F8) · 500 은 `DEBUG=True` 디버그 페이지 (F9) | 개선 4: 짧은 재시도 · FAILURE + 503 | 105.2초 → 16.1초 · 503 · job 34 FAILURE ([be_f8_redis_v1.txt](evidence/logs/be_f8_redis_v1.txt)) |
| 작업이 영원히 PENDING · 삭제하면 409 | Redis 장애로 메시지가 큐에 들어가지 못함 · 「진행 중 삭제 금지」가 멈춘 작업에도 적용 | 개선 4: `is_stale` (PENDING 10분) 이면 삭제 허용 · 개선 전 job 18 · 19 는 기록으로 보존 | 테스트 `test_stale_pending_can_be_deleted` · [admin_pending_jobs_f8.png](images/admin_pending_jobs_f8.png) |
| Worker 가 꺼져 있으면 화면이 끝없이 「대기」 | 폴링에 끝나는 조건이 `is_finished` 뿐 (F4) | 개선 5: 최대 10분 · `is_stale` 이면 멈추고 안내 | [be_f4_poll_v1.txt](evidence/logs/be_f4_poll_v1.txt) |
| IP Webcam 분석이 FAILURE 「카메라에 연결하지 못했습니다. 휴대폰 IP Webcam 앱이 켜져 있고 같은 네트워크인지 확인하세요.」 | 휴대폰 앱이 꺼졌거나 다른 네트워크 · Celery 로그 `Connection to tcp://<카메라-IP>:8080 failed: Connection refused` | 앱을 켜고 같은 Wi-Fi 확인 · 주소는 `.env` `IP_WEBCAM_ALLOWED_URLS` | 실패는 예외 없이 FAILURE + 이유로 저장 (T09 · [celery_log2.txt](evidence/logs/celery_log2.txt) · [screen_webcam_failure.png](images/screen_webcam_failure.png)) |
| 미리보기가 안 나오고 502 | 카메라 꺼짐 또는 MJPEG 가 아닌 주소 | 앱 켜기 · `/video` (MJPEG) 주소 사용 | 응답에 카메라 주소를 넣지 않음 ([stream_502_camera_off.png](images/stream_502_camera_off.png)) |
| Docker(PostgreSQL) 에서 테스트 9개 ERROR (`test_camera_preview`) | 테스트 안의 `res.close()` (브라우저 끊김 흉내) 가 `request_finished` 신호 → `close_old_connections` 를 불러 테스트용 PostgreSQL 연결을 닫음 (`OperationalError: the connection is closed` 9번) · 기능 고장이 아니라 테스트 환경 문제 | 6521481: 테스트 클라이언트 대신 `RequestFactory` 로 뷰를 직접 부르고 신호를 잠시 떼어 냄 | 47개 통과 → 정리 뒤 51개 통과 ([tests_docker_20261124_fail.txt](evidence/logs/tests_docker_20261124_fail.txt) · [tests_docker_dedupe_pass.txt](evidence/logs/tests_docker_dedupe_pass.txt)) |
| 주소창에 `/accounts/logout/` 을 치면 405 | Django 5.2 `LogoutView` 는 POST 만 받음 | 화면 오른쪽 위 「로그아웃」 버튼 (`base.html` POST 폼) 사용 | [logout_post_302.png](images/logout_post_302.png) (POST → 302 → `/accounts/login/`) |
| 일반 회원이 「대시보드」로 가면 로그인 화면 | `@staff_member_required` → 302 `/admin/login/` | 관리자 계정으로 접속 (의도된 동작) | [dashboard_user_denied.png](images/dashboard_user_denied.png) |
| 웹캠 손 흔들기가 `sit_stand` · `drink_return` 으로 나옴 | 모델이 한 사람 · 클립 6개로 학습됨 · 해상도 · 방향 · Pose conf 를 바꿔도 같음 | 코드는 그대로 두고 0.55 미만은 「판단 불확실」로 표시 | [webcam_retry_compare.txt](evidence/logs/webcam_retry_compare.txt) · [ai-inference.md](ai-inference.md#6-데이터-한계) |

포트와 컨테이너 확인

```bash
docker compose ps
docker ps
ss -ltnp
```
