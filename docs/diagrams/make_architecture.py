"""Vision Action Platform Architecture (yolo-kimchi-inspection-project 방식, 개발자용 상세판 v5)
기준: GitHub main 40d3916 (compose.yaml · backend · ai_service) 실제 코드
python3 make_architecture.py        ->  architecture.svg     (한국어)
python3 make_architecture.py en     ->  architecture.en.svg  (영어, translate_architecture_en.py 가 부름)
"""
import sys
from pathlib import Path

LANG = sys.argv[1] if len(sys.argv) > 1 else "ko"


def T(ko, en=None):
    """한국어 / 영어 한 쌍. 영어판이면 en, 없으면(코드 · 경로뿐인 글자) 그대로."""
    return en if (LANG == "en" and en is not None) else ko


FONT = "Noto Sans CJK KR, Malgun Gothic, sans-serif"
INK, SUB, LINE = "#1E293B", "#475569", "#94A3B8"
GRAY, PURPLE, BLUE, TEAL = "#475569", "#6D28D9", "#2563EB", "#0E7490"

# ── 레이아웃: 빔 프로젝터에서도 읽히게 글자를 키우고 칸을 넓힘 ──
PITCH, X0 = 380, 210
CARD_W = 358
NODE_W, NODE_H = 240, 200
W = X0 + PITCH * 7 + CARD_W // 2 + 40
F_CT, F_CL, LH = 18, 15, 23          # 카드 제목 · 카드 글자 · 줄 간격
WARN = []


def tw(s, size, bold=False):
    """글자 폭 어림값(px): 한글 1em, 영문 · 숫자 약 0.56em"""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o >= 0x2E80 or 0x2460 <= o <= 0x24FF:
            w += 1.0
        elif ch in "MWm@%&":
            w += 0.85
        elif ch in " .,:;'|!il()[]{}·/":
            w += 0.34
        else:
            w += 0.58
    return w * size * (1.06 if bold else 1.0)


def fit(s, size, width, where, bold=False):
    if tw(s, size, bold) > width:
        WARN.append(f"{where}: {s!r} {tw(s, size, bold):.0f}>{width:.0f}")


ICONS = {
    "monitor": '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
    "api": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 9h18"/><path d="M7 13h4M7 16h7"/>',
    "queue": '<path d="M4 7h16M4 12h16M4 17h10"/>',
    "cycle": '<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v5h-5"/>',
    "bolt": '<path d="M13 3L5 14h6l-1 7 8-11h-6z"/>',
    "person": '<circle cx="12" cy="4.5" r="2"/><path d="M12 7v7M7 10l5 2 5-2M9 21l3-7 3 7"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "tree": '<path d="M12 3l5 7h-3l4 6H6l4-6H7z"/><path d="M12 16v5"/>',
    "db": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 13h6M9 17h6"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "play": '<circle cx="12" cy="12" r="9"/><path d="M10 8l6 4-6 4z"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1L7 17M17 7l2.1-2.1"/>',
    "list": '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="5" cy="6" r="1.2"/><circle cx="5" cy="12" r="1.2"/><circle cx="5" cy="18" r="1.2"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "alert": '<path d="M12 3l9.5 17h-19z"/><path d="M12 10v4M12 17.5v.5"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "inbox": '<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5 5h14l2 8v6H3v-6z"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-5-5"/>',
    "chart": '<path d="M4 20V10M10 20V5M16 20v-7M3 20h18"/>',
    "branch": '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="8" r="2"/><path d="M6 7v10M18 10c0 4-6 3-12 7"/>',
    "route": '<circle cx="5" cy="6" r="2"/><circle cx="19" cy="18" r="2"/><path d="M7 6h7a3 3 0 0 1 0 6H10a3 3 0 0 0 0 6h7"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4-6 8-6s7 2 8 6"/>',
    "camera": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7l2-3h4l2 3"/><circle cx="12" cy="13.5" r="3.5"/>',
    "heart": '<path d="M3 12h4l2-5 4 10 2-5h6"/>',
    "box": '<path d="M12 3l9 5v8l-9 5-9-5V8z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
    "check": '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 12l3 3 5-6"/>',
    "table": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M3 14h18M10 4v16"/>',
    "json": '<path d="M9 4c-2 0-3 1-3 3v2c0 1.5-1 3-2 3 1 0 2 1.5 2 3v2c0 2 1 3 3 3M15 4c2 0 3 1 3 3v2c0 1.5 1 3 2 3-1 0-2 1.5-2 3v2c0 2-1 3-3 3"/>',
}


def icon(name, x, y, scale=1.0, color=SUB, width=1.8):
    return (f'<g transform="translate({x},{y}) scale({scale})" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>')


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cx(i):
    return X0 + PITCH * i


out = []
add = out.append

# ════════════════════════════════════════════════════════════════════
# 글자 (한국어, 영어)
# ════════════════════════════════════════════════════════════════════
TITLE = "Architecture · Vision Action Platform"
SUBTITLE = T("버튼 1번 = 위 줄(1 → 8) 분석 요청이 AI 까지 가는 길 → 아래 줄(9 → 12) 결과가 PostgreSQL 에 저장되고 화면으로 돌아오는 길 · 화살표 위 = 오가는 데이터 형식",
             "One click = top row (1 → 8) the request travels to the AI → bottom row (9 → 12) the result is saved in PostgreSQL and comes back to the screen · above each arrow = data format")
SEC_A = T("backend/ · django + celery (같은 이미지) — 요청 접수 · 작업 저장 · 큐 등록 · 영상 확보",
          "backend/ · django + celery (same image) — accept request · save job · enqueue · get video")
SEC_B = T("ai_service/ · fastapi — 영상 → 사람별 동작 예측 JSON 만 반환 (DB 접근 없음)",
          "ai_service/ · fastapi — video → per-person action JSON only (no DB access)")

top_cards = [
    ("play", T("시작: 화면 주소 (로그인 필요)", "Start: page URL (login)"),
     ["GET / → config/urls.py path(\"\")",
      "→ analyses/urls.py → page_views.index",
      T("  @login_required (미로그인 → 로그인)", "  @login_required (else → login)"),
      "→ index.html  data-list-url =",
      "  {% url 'api:analysis-list' %}",
      "→ static/js/analyses.js (WhiteNoise)"]),
    ("route", T("주소 따라가기 (API)", "Follow the URL (API)"),
     ["config/urls.py path(\"api/v1/\")",
      "→ config/api_urls.py (app_name=\"api\")",
      "→ analyses/api_urls.py",
      "  router.register(\"analyses\", ...)",
      "→ views.AnalysisJobViewSet.create()",
      T("SessionAuth · IsAuthenticated 검사", "SessionAuth · IsAuthenticated")]),
    ("link", T("연결 설정", "Connection settings"),
     [".env CELERY_BROKER_URL",
      "  = redis://redis:6379/0",
      "CELERY_RESULT_BACKEND = .../1",
      "config/celery.py: Celery(\"config\")",
      "  autodiscover_tasks() → tasks.py",
      T("등록 재시도 max_retries 2 · 연결 3초", "retry max_retries 2 · connect 3 s")]),
    ("list", T("처리 순서 (analyses/tasks.py)", "Steps (analyses/tasks.py)"),
     [T("① get(pk=job_id) → STARTED 저장", "① get(pk=job_id) → save STARTED"),
      T("② _prepare_video(job) → mp4 경로", "② _prepare_video(job) → mp4 path"),
      "③ services.predict_video(path, job_id)",
      T("④ save_result(job, data) → 9 번", "④ save_result(job, data) → node 9"),
      T("오류 → _fail(job, message) · FAILURE", "error → _fail(job, message) · FAILURE"),
      T("제한 600초 (soft 570초)", "time limit 600 s (soft 570 s)")]),
    ("play", T("시작: main.py lifespan (1번)", "Start: main.py lifespan (once)"),
     ["uvicorn main:app --port 8001",
      "load_project_config() ← project.json",
      T("load_action_model() ← models/ 3개 검사", "load_action_model() ← checks 3 files"),
      "PosePipeline(config) ← yolo11n-pose.pt",
      T("→ app.state 에 두고 요청마다 재사용", "→ kept in app.state, reused"),
      T("실패 → /health degraded · 503", "failure → /health degraded · 503")]),
    ("gear", T("설정 · ai_service/project.json", "ai_service/project.json"),
     ["pose_model yolo11n-pose.pt",
      "image_size 640 · person_confidence 0.25",
      "day08_multi_person.tracker",
      "  = bytetrack.yaml · lost 2.0 s",
      T(".env POSE_DEVICE=cpu · POSE_WEIGHTS", ".env POSE_DEVICE=cpu · POSE_WEIGHTS"),
      T("MAX_VIDEO_SECONDS 60 (긴 영상 자름)", "MAX_VIDEO_SECONDS 60 (cut longer)")]),
    ("list", T("38-D Frame Feature (사람 1명)", "38-D frame feature (1 person)"),
     ["src/multi_person_utils.py",
      "  feature_from_keypoints(kp)",
      T("normalize_by_shoulder_width → 34", "normalize_by_shoulder_width → 34"),
      T("selected_joint_angles → 4 (팔꿈치 · 무릎)", "selected_joint_angles → 4 (elbow · knee)"),
      T("함수: src/feature_utils.py", "functions: src/feature_utils.py"),
      T("모양 안 맞으면 None (빈칸)", "bad shape → None (gap)")]),
    ("lock", T("모델 · ai_service/models/ (ro)", "ai_service/models/ (ro)"),
     [T("rf_action_baseline.joblib  모델", "rf_action_baseline.joblib  model"),
      T("rf_feature_columns.json  1,140 순서", "rf_feature_columns.json  1,140 order"),
      T("rf_training_info.json  steps 30 · 6", "rf_training_info.json  steps 30 · 6"),
      T("검사: n_features_in_ = 1,140", "check: n_features_in_ = 1,140"),
      T("  컬럼 = sequence_feature_names(30)", "  cols = sequence_feature_names(30)"),
      T("compose → /app/models (읽기 전용)", "compose → /app/models (read-only)")]),
]

bot_cards = [
    ("file", T("보내는 값 · multipart FormData", "Sent · multipart FormData"),
     ["input_type: UPLOAD / WEBCAM",
      T("video_file 또는 camera_index", "video_file or camera_index"),
      "title · memo · expected_action",
      T("헤더 X-CSRFToken · 세션 쿠키", "header X-CSRFToken · session cookie"),
      T("← 202 JSON {id, task_id, status,", "← 202 JSON {id, task_id, status,"),
      "     status_url}"]),
    ("shield", T("serializers.py 검사 → 저장", "serializers.py check → save"),
     ["AnalysisJobCreateSerializer",
      T("  mp4 · mov · avi · mkv · 최대 100MB", "  mp4 · mov · avi · mkv · max 100MB"),
      T("  WEBCAM: 허용 목록 카메라 번호만", "  WEBCAM: allowed camera index only"),
      T("save(user, celery_task_id=uuid4)", "save(user, celery_task_id=uuid4)"),
      T("  → AnalysisJob 1행 PENDING", "  → 1 AnalysisJob row PENDING"),
      T("on_commit → enqueue_analysis()", "on_commit → enqueue_analysis()"),
      T("  Redis 등록 실패 → FAILURE · 503", "  enqueue fails → FAILURE · 503")]),
    ("inbox", T("Redis 가 갖는 것", "What Redis holds"),
     [T("작업 메시지: run_analysis · [job_id]", "task message: run_analysis · [job_id]"),
      "  + task_id (uuid4)",
      T("결과 /1: 반환값 {job_id, status} 만", "result /1: return {job_id, status} only"),
      T("업무 데이터는 PostgreSQL 에만", "business data only in PostgreSQL"),
      T("포트 공개 안 함 (compose 내부)", "port not published (compose only)")]),
    ("clock", T("영상 확보 · 작업 로그", "Get video · job log"),
     [T("UPLOAD: media/videos/YYYY/MM/DD/", "UPLOAD: media/videos/YYYY/MM/DD/"),
      T("WEBCAM: capture_clip() 8초 · 30fps", "WEBCAM: capture_clip() 8 s · 30 fps"),
      "  → media/captures/.../job_{id}.mp4",
      T("media_data 볼륨 (django ↔ celery)", "media_data volume (django ↔ celery)"),
      T("로그 job#N: 대기 · 영상 · 추론 · 저장 초", "log job#N: wait · video · AI · save s"),
      T("  시각 +0900 (KST)", "  time +0900 (KST)")]),
    ("alert", T("FastAPI 오류 → FAILURE", "FastAPI errors → FAILURE"),
     [T("400 확장자 · 빈 파일", "400 extension · empty file"),
      T("413 100MB 초과", "413 over 100MB"),
      T("422 영상 못 읽음 (VideoReadError)", "422 unreadable video (VideoReadError)"),
      T("503 모델 미준비 (load_error)", "503 model not ready (load_error)"),
      T("→ services.py AIServiceError → _fail", "→ services.py AIServiceError → _fail"),
      T("로그 job#N (X-Job-ID 헤더)", "log job#N (X-Job-ID header)")]),
    ("search", "probe_video() → model.track()",
     ["fps · frames · duration_sec",
      "stream=True · persist=False",
      T("프레임마다 boxes.id = track_id", "per frame boxes.id = track_id"),
      T("영상 시각 t = frame_idx / fps", "video time t = frame_idx / fps"),
      T("사람 없음 → tracks [] ", "no person → tracks []"),
      "  → person_found false"]),
    ("clock", T("30 Step 만들기 (Window)", "Build 30 steps (window)"),
     ["src/realtime_utils.py",
      T("TimedFeatureBuffer 5초", "TimedFeatureBuffer 5 s"),
      "  is_ready(0.8, 0.6, 10)",
      "resample_sequence → (30, 38)",
      "flatten_sequence → (1, 1140)",
      T("5초 못 채움 → whole_track 1번", "under 5 s → whole_track once")]),
    ("tree", T("결과 정리", "Summarize"),
     [T("0.25초마다 predict_proba", "predict_proba every 0.25 s"),
      T("Window 확률 평균 → argmax", "mean of window probs → argmax"),
      T("열 순서 = model.classes_", "column order = model.classes_"),
      "→ action_label · confidence",
      "  windows · frame_count",
      "  probabilities {6 classes}"]),
]

nodes_a = [
    ("monitor", T("브라우저", "Browser"), T("분석 화면 · 버튼 클릭", "analysis page · click"),
     "templates/analyses/index.html", "static/js/analyses.js", GRAY, None),
    ("api", "Django · DRF", T("요청 접수 · 작업 저장 · 큐 등록", "accept · save job · enqueue"),
     "analyses/views.py", "AnalysisJobViewSet.create()", PURPLE, "django :8000"),
    ("queue", "Redis", T("작업 대기열 (Celery 브로커)", "job queue (Celery broker)"),
     "redis://redis:6379/0", T("메시지 = run_analysis", "message = run_analysis"), PURPLE, "redis"),
    ("cycle", "Celery Worker", T("영상 확보 · AI 호출 · 결과 저장", "get video · call AI · save"),
     "analyses/tasks.py", "run_analysis(job_id)", PURPLE, "celery"),
    ("bolt", "FastAPI", T("영상 받기 · 검사 · 추론 입구", "receive · check · infer"),
     "routers/predictions.py", "predict_video()", BLUE, "fastapi :8001"),
    ("person", "YOLO Pose", T("사람 찾기 · 추적 · 관절 17개", "find · track · 17 joints"),
     "services/pose_pipeline.py", "PosePipeline.process_video()", BLUE, T("fastapi 안", "in fastapi")),
    ("layers", "38-D → 1,140", T("관절 → 모델 입력 숫자", "joints → model input"),
     "src/multi_person_utils.py", "feature_from_keypoints()", TEAL, T("fastapi 안", "in fastapi")),
    ("tree", "RandomForest", T("6개 동작 확률 → Label", "6 action probs → label"),
     "services/action_inference.py", "predict_tracks()", TEAL, T("fastapi 안", "in fastapi")),
]

arrows_a = [
    (["POST /api/v1/", "analyses/", "FormData"], [T("분석 요청", "request"), T("← 202 JSON", "← 202 JSON")]),
    (["apply_async", "([pk], task_id)"], [T("Redis 메시지", "Redis message"), T("커밋 뒤 등록", "after commit")]),
    (["run_analysis", "(job_id)"], [T("Worker 가", "worker"), T("꺼내 실행", "takes it")]),
    (["POST", "/predict/video", "multipart mp4"], [T("영상 파일 전송", "send video")]),
    (["process_video", "(tmp.name)"], [T("임시 mp4 경로", "temp mp4 path")]),
    (["keypoints.xy", T("(사람, 17, 2)", "(people, 17, 2)")], [T("사람별 관절", "joints per"), T("좌표 배열", "person")]),
    (["ndarray", "(1, 1140)"], [T("Window 당", "1,140 numbers"), T("1,140개 숫자", "per window")]),
]

LANE_LABEL = "200 JSON {person_found · message · processing_ms · video{frames, fps} · predictions[track_id · action_label · confidence · windows · probabilities]}"
LANE_SUB = T("추론 결과 반환 → 같은 run_analysis 안에서 services.predict_video() 가 dict 로 받아 save_result(job, data) 로 넘김",
             "result returned → inside the same run_analysis, services.predict_video() gets a dict and passes it to save_result(job, data)")

nodes_b = [
    (3, 9, "cycle", "Celery Worker", T("결과 검사 · DB 저장", "check result · save to DB"),
     "analyses/tasks.py", "save_result(job, data)", PURPLE, "celery"),
    (2, 10, "db", "PostgreSQL 16", T("작업 1 : N 사람별 예측", "job 1 : N predictions"),
     "analyses/models.py", "AnalysisJob · PersonPrediction", BLUE, "postgres :5432"),
    (1, 11, "api", "Django · DRF", T("본인 작업만 조회 · JSON 응답", "own jobs only · JSON"),
     "views.py · serializers.py", "status() · retrieve()", PURPLE, "django :8000"),
    (0, 12, "monitor", T("브라우저", "Browser"), T("상태 표시 · 사람별 결과 표", "status · result table"),
     "static/js/analyses.js", "poll() · showResult()", GRAY, None),
]
arrows_b = [
    (["bulk_create", "+ job.save()"], [T("ORM 행 저장", "ORM rows")]),
    (["visible_to", "(user)"], [T("작업 · 예측", "read job ·"), T("읽기", "predictions")]),
    ([T("상태 JSON", "status JSON"), T("결과 JSON", "result JSON")], [T("2초 폴링", "poll 2 s"), T("최대 10분", "max 10 min")]),
]
b_cards = [
    ("list", T("save_result() 순서", "save_result() steps"),
     [T("action_label ∈ ActionLabel 6개 확인", "action_label ∈ ActionLabel (6)"),
      T("  밖이면 AIServiceError → _fail", "  else AIServiceError → _fail"),
      "transaction.atomic():",
      T("  기존 예측 delete → bulk_create", "  delete old → bulk_create"),
      "job: SUCCESS · video_* · processing_ms",
      "  result_message · finished_at"]),
    ("table", T("테이블 (Django ORM)", "Tables (Django ORM)"),
     ["auth_user 1 ─ N analysisjob 1 ─ N",
      "  personprediction",
      T("job: user · input_type · status", "job: user · input_type · status"),
      T("  celery_task_id · video_file 경로", "  celery_task_id · video_file path"),
      "pred: track_id · action_label",
      "  confidence · probabilities (JSON)"]),
    ("json", T("응답 JSON (serializers.py)", "Response JSON (serializers.py)"),
     ["status/ → AnalysisJobStatusSerializer",
      "  status · is_finished · is_stale",
      T("  prediction_count (COUNT 만)", "  prediction_count (COUNT only)"),
      "{id}/ → AnalysisJobSerializer",
      T("  + predictions[] · is_uncertain", "  + predictions[] · is_uncertain"),
      T("남의 작업 id → 404 (visible_to)", "other user's id → 404 (visible_to)")]),
    ("monitor", T("화면 표시 (analyses.js)", "Display (analyses.js)"),
     [T("poll(): 2초마다 GET status/", "poll(): GET status/ every 2 s"),
      T("  10분 넘으면 멈추고 안내", "  stops after 10 min with notice"),
      T("is_stale → 멈춘 작업 안내", "is_stale → stuck job notice"),
      T("SUCCESS → showResult(): GET {id}/", "SUCCESS → showResult(): GET {id}/"),
      T("is_uncertain → '판단 불확실' 배지", "is_uncertain → 'uncertain' badge"),
      T("상세 /analyses/{id}/ 링크", "link to /analyses/{id}/")]),
]

side_admin = (T("관리자 화면 · is_staff 만", "Admin screens · is_staff only"),
              ["GET /dashboard/ → page_views.dashboard (@staff_member_required)",
               T("_count_by() GROUP BY · Avg(processing_ms) → chart_data", "_count_by() GROUP BY · Avg(processing_ms) → chart_data"),
               T("dashboard.html json_script → static/js/dashboard.js · Chart.js 4개", "dashboard.html json_script → static/js/dashboard.js · 4 Chart.js charts"),
               T("/admin/ → admin.py AnalysisJobAdmin (예측 수 annotate · 필터)", "/admin/ → admin.py AnalysisJobAdmin (prediction count annotate · filters)"),
               T("/analyses/{id}/ → page_views.detail (visible_to · 남의 것 404)", "/analyses/{id}/ → page_views.detail (visible_to · others 404)"),
               T("브라우저 → django :8000 (FastAPI 는 DB 를 모름)", "browser → django :8000 (FastAPI never sees the DB)")])
side_cam = (T("웹캠 실시간 미리보기 · django", "Webcam live preview · django"),
            [T("WEBCAM 탭 → <img src=\"/cameras/<index>/stream/\">", "WEBCAM tab → <img src=\"/cameras/<index>/stream/\">"),
             T("analyses/urls.py → stream_views.camera_stream (@login_required · GET)", "analyses/urls.py → stream_views.camera_stream (@login_required · GET)"),
             T("get_allowed_camera_url(index): 허용 목록 밖 → 404", "get_allowed_camera_url(index): not in allow list → 404"),
             T("requests.get(stream) → MJPEG 바이트 그대로 중계 (재압축 없음)", "requests.get(stream) → relays MJPEG bytes as-is (no re-encode)"),
             T("CAMERA_PREVIEW_MAX_SECONDS 60초 · 카메라 실패 502", "CAMERA_PREVIEW_MAX_SECONDS 60 s · camera down 502"),
             T("카메라 IP 는 브라우저에 안 보임 · 분석 수집(capture_clip)과 별도", "camera IP never reaches the browser · separate from capture_clip")])
side_acc = (T("회원 · accounts/ (화면)", "Accounts · accounts/ (pages)"),
            [T("/accounts/signup/ → views.signup (SignUpForm) → 가입 후 바로 login", "/accounts/signup/ → views.signup (SignUpForm) → logs in right away"),
             T("/accounts/login/ → LoginView (redirect_authenticated_user) · 세션 쿠키", "/accounts/login/ → LoginView (redirect_authenticated_user) · session cookie"),
             T("/accounts/logout/ → LogoutView (POST 로만)", "/accounts/logout/ → LogoutView (POST only)"),
             T("GET /api/v1/auth/me/ → accounts.views.me → MeSerializer", "GET /api/v1/auth/me/ → accounts.views.me → MeSerializer"),
             "  {id, username, email, is_staff, date_joined}"])
side_health = (T("헬스체크 · 시작 순서", "Health checks · start order"),
               [T("GET /api/v1/health/ → config/health.py (로그인 불필요 · GET 만)", "GET /api/v1/health/ → config/health.py (no login · GET only)"),
                T("_check_db: SELECT 1 · _check_redis: ping (2초 제한)", "_check_db: SELECT 1 · _check_redis: ping (2 s timeout)"),
                T("200 {status: ok, checks{db, redis: ms}} · 하나라도 실패 503", "200 {status: ok, checks{db, redis: ms}} · any failure 503"),
                T("FastAPI GET /health → model_loaded · classes · n_features", "FastAPI GET /health → model_loaded · classes · n_features"),
                T("compose healthcheck → depends_on service_healthy 순서로 시작", "compose healthcheck → depends_on service_healthy start order")])
side_compose = (T("compose.yaml · 5개 서비스 (docker compose up --build) · .env ← .env.example", "compose.yaml · 5 services (docker compose up --build) · .env ← .env.example"),
                [T("postgres:16-alpine · 5432 내부 · 볼륨 postgres_data · pg_isready", "postgres:16-alpine · 5432 internal · volume postgres_data · pg_isready"),
                 T("redis:7-alpine · 6379 내부 · redis-cli ping", "redis:7-alpine · 6379 internal · redis-cli ping"),
                 T("fastapi · 127.0.0.1:8001 (내 PC 만) · ./ai_service/models:/app/models:ro · GET /health", "fastapi · 127.0.0.1:8001 (this PC only) · ./ai_service/models:/app/models:ro · GET /health"),
                 T("django · 8000:8000 · migrate → gunicorn --workers 3 · media_data · GET /api/v1/health/", "django · 8000:8000 · migrate → gunicorn --workers 3 · media_data · GET /api/v1/health/"),
                 T("celery · 같은 backend 이미지 · --concurrency=2 · media_data · fastapi healthy 뒤 시작", "celery · same backend image · --concurrency=2 · media_data · starts after fastapi healthy"),
                 T(".env: DJANGO_* · POSTGRES_* · CELERY_BROKER_URL · AI_SERVICE_URL · IP_WEBCAM_ALLOWED_URLS · RF_*_FILE", ".env: DJANGO_* · POSTGRES_* · CELERY_BROKER_URL · AI_SERVICE_URL · IP_WEBCAM_ALLOWED_URLS · RF_*_FILE"),
                 T("TZ=Asia/Seoul (fastapi · django · celery 로그 시각 KST)", "TZ=Asia/Seoul (fastapi · django · celery log times in KST)")])
side_tests = (T("검증 · 실행 순서 아님 · 자동 테스트 51개", "Verification · not a runtime step · 51 tests"),
              [T("docker compose exec django python manage.py test → 51 OK", "docker compose exec django python manage.py test → 51 OK"),
               T("analyses/tests.py 36: 202 · 400 · 404 · 409 · 503 · 상태 · 로그", "analyses/tests.py 36: 202 · 400 · 404 · 409 · 503 · status · logs"),
               T("  /api/v1 주소 · health · 멈춘 작업 · 쿼리 수 · is_uncertain", "  /api/v1 URLs · health · stuck jobs · query count · is_uncertain"),
               T("analyses/test_camera_preview.py 10: 로그인 · 404 · 60초 · 502", "analyses/test_camera_preview.py 10: login · 404 · 60 s · 502"),
               T("accounts/tests.py 5: 가입 · 로그인/로그아웃 · 차단 · auth/me", "accounts/tests.py 5: signup · login/logout · blocked · auth/me"),
               T("Celery eager · predict_video 는 mock → Redis · AI 없이 실행", "Celery eager · predict_video mocked → runs without Redis · AI"),
               T("화살표 없음: 코드를 바꾸지 않고 확인만 함", "no arrows: checks only, changes nothing")])
side_git = ("GitHub · vision-action-platform → main",
            [T("코드 · README · docs · .env.example 만 올림", "code · README · docs · .env.example only"),
             T(".env · *.joblib · *.pt · media 영상은 올리지 않음", ".env · *.joblib · *.pt · media videos stay local"),
             T("rf_feature_columns.json · rf_training_info.json 은 레포에 있음", "rf_feature_columns.json · rf_training_info.json are in the repo"),
             T("모델 2개는 README '모델 준비' 대로 models/ 에 복사", "copy the 2 model files into models/ as in the README"),
             T("볼륨: postgres_data (DB) · media_data (영상 공유)", "volumes: postgres_data (DB) · media_data (shared videos)")])

LBL_PENDING = T("INSERT AnalysisJob (PENDING)", "INSERT AnalysisJob (PENDING)")
LBL_STARTED = T("UPDATE STARTED · FAILURE(_fail)", "UPDATE STARTED · FAILURE(_fail)")
LBL_ADMIN = T("ORM 집계 → 관리자", "ORM aggregate → admin")
LEGEND = T("굵은 화살표 = 요청 · 데이터가 가는 길 (위 = 코드 호출 · 데이터 형식, 아래 = 쉬운 설명) · 파란 점선 = Django ORM 으로 PostgreSQL 에 쓰는 지점 · 회색 실선 = ORM 조회 · 회색 점선 칸 = 검증 (실행 흐름 아님) · 회색 태그 = compose.yaml 서비스 · 포트",
           "Thick arrow = request / data path (above = code call · data format, below = plain words) · blue dashed = Django ORM writes to PostgreSQL · gray line = ORM read · gray dashed box = verification (not runtime) · gray tag = compose.yaml service · port")


# ── 주소(엔드포인트) 표: config/urls.py · config/api_urls.py · analyses/api_urls.py · analyses/urls.py
#    accounts/urls.py · ai_service/main.py · routers/predictions.py (40d3916) 에서 확인 ──
EP_TITLE = T("주소(엔드포인트) 표 · 메서드 · 처리 파일 · 함수 · 응답 코드 · 지나는 노드 (번호 = 위 그림 원 번호)",
             "Endpoint table · method · handler file · function · status codes · nodes passed (numbers = circles above)")
EP_HEAD = [T("메서드", "Method"), T("주소", "URL"), T("처리 파일 · 함수", "Handler file · function"),
           T("응답 코드", "Status codes"), T("지나는 노드", "Nodes passed")]
EP = [
    ("group", T("화면 (django :8000 · HTML · 로그인 안 했으면 302 → /accounts/login/)", "Pages (django :8000 · HTML · not logged in → 302 /accounts/login/)")),
    ("GET", "/", T("analyses/urls.py → page_views.index (@login_required)", "analyses/urls.py → page_views.index (@login_required)"),
     T("200 분석 화면 · 302 미로그인", "200 analysis page · 302 not logged in"), "① → ②"),
    ("GET", "/analyses/<id>/", T("page_views.detail (@login_required · visible_to)", "page_views.detail (@login_required · visible_to)"),
     T("200 · 302 · 404 남의 작업 · 없는 id", "200 · 302 · 404 other user's job · no such id"), "⑫ → ⑪ → ⑩"),
    ("GET", "/dashboard/", T("page_views.dashboard (@staff_member_required)", "page_views.dashboard (@staff_member_required)"),
     T("200 · 302 is_staff 아님 → /admin/login/", "200 · 302 not staff → /admin/login/"), T("관리자 화면 → ⑩ (ORM 집계)", "admin box → ⑩ (ORM aggregate)")),
    ("GET", "/cameras/<index>/stream/", T("stream_views.camera_stream (@login_required · @require_GET)", "stream_views.camera_stream (@login_required · @require_GET)"),
     T("200 MJPEG 스트림 · 302 · 404 허용 목록 밖 · 405 GET 아님 · 502 카메라 실패 · MJPEG 아님", "200 MJPEG stream · 302 · 404 not in allow list · 405 not GET · 502 camera down · not MJPEG"),
     T("① → ② → 휴대폰 (웹캠 미리보기 칸)", "① → ② → phone (webcam preview box)")),
    ("GET POST", "/accounts/signup/", T("accounts/urls.py → views.signup (SignUpForm)", "accounts/urls.py → views.signup (SignUpForm)"),
     T("200 가입 폼 · 302 가입 후 바로 로그인 → /", "200 signup form · 302 logged in right away → /"), T("① → ② → ⑩ (auth_user)", "① → ② → ⑩ (auth_user)")),
    ("GET POST", "/accounts/login/", "auth_views.LoginView (redirect_authenticated_user=True)",
     T("200 로그인 폼 · 302 성공 → / (세션 쿠키)", "200 login form · 302 success → / (session cookie)"), T("① → ② → ⑩ (auth_user)", "① → ② → ⑩ (auth_user)")),
    ("POST", "/accounts/logout/", T("auth_views.LogoutView (POST 만)", "auth_views.LogoutView (POST only)"),
     T("302 → /accounts/login/ · GET 은 405", "302 → /accounts/login/ · GET is 405"), "① → ②"),
    ("GET POST", "/admin/", "config/urls.py → admin.site.urls · analyses/admin.py",
     T("200 · 302 → /admin/login/ (is_staff 만)", "200 · 302 → /admin/login/ (staff only)"), T("관리자 화면 → ⑩", "admin box → ⑩")),
    ("group", T("API (/api/v1/ · JSON · 세션 로그인 · 로그인 안 했으면 403 · health 만 예외 · PUT 은 405)", "API (/api/v1/ · JSON · session login · not logged in → 403 · except health · PUT → 405)")),
    ("GET", "/api/v1/analyses/", T("analyses/api_urls.py router → AnalysisJobViewSet.list()", "analyses/api_urls.py router → AnalysisJobViewSet.list()"),
     T("200 {count, next, previous, results} 20개씩 (관리자 전체) · 403", "200 {count, next, previous, results} 20 per page (staff: all) · 403"), "⑪ → ⑩"),
    ("POST", "/api/v1/analyses/", "AnalysisJobViewSet.create() · AnalysisJobCreateSerializer",
     T("202 {id, task_id, status, status_url} · 400 입력 오류 · 403 · 503 Redis 등록 실패", "202 {id, task_id, status, status_url} · 400 invalid input · 403 · 503 enqueue failed"),
     T("① → ② → ⑩ INSERT → ③ → ④ …", "① → ② → ⑩ INSERT → ③ → ④ …")),
    ("GET", "/api/v1/analyses/<id>/", "retrieve() → AnalysisJobSerializer + predictions",
     T("200 · 403 · 404 남의 작업 · 없는 id", "200 · 403 · 404 other user's job · no such id"), "⑫ → ⑪ → ⑩"),
    ("PATCH", "/api/v1/analyses/<id>/", T("partial_update() → AnalysisJobUpdateSerializer (title · memo 만)", "partial_update() → AnalysisJobUpdateSerializer (title · memo only)"),
     "200 · 400 · 403 · 404", "⑪ → ⑩"),
    ("DELETE", "/api/v1/analyses/<id>/", T("destroy() · 예측 CASCADE · 영상 파일도 삭제", "destroy() · predictions CASCADE · video file removed"),
     T("204 · 409 처리 중 (멈춘 작업 is_stale 은 허용) · 403 · 404", "204 · 409 still running (stuck is_stale allowed) · 403 · 404"), T("⑪ → ⑩ (+ media_data)", "⑪ → ⑩ (+ media_data)")),
    ("GET", "/api/v1/analyses/<id>/status/", T("@action status() → AnalysisJobStatusSerializer (Count 만)", "@action status() → AnalysisJobStatusSerializer (Count only)"),
     T("200 {status, is_finished, is_stale, prediction_count, …} · 403 · 404", "200 {status, is_finished, is_stale, prediction_count, …} · 403 · 404"),
     T("⑫ → ⑪ → ⑩ (2초 폴링)", "⑫ → ⑪ → ⑩ (poll 2 s)")),
    ("GET", "/api/v1/auth/me/", "config/api_urls.py → accounts.views.me → MeSerializer",
     "200 {id, username, email, is_staff, date_joined} · 403 · 405", "① → ②"),
    ("GET", "/api/v1/health/", T("config/api_urls.py → config/health.py health() · 로그인 불필요", "config/api_urls.py → config/health.py health() · no login"),
     T("200 {status: ok, checks{db, redis}} · 503 DB · Redis 실패 · 405 GET 아님", "200 {status: ok, checks{db, redis}} · 503 DB · Redis down · 405 not GET"),
     T("② → ⑩ SELECT 1 · ③ ping", "② → ⑩ SELECT 1 · ③ ping")),
    ("group", T("FastAPI (:8001 · 127.0.0.1 에만 공개 · Celery 는 http://fastapi:8001 로 부름 · DB 없음)", "FastAPI (:8001 · published on 127.0.0.1 only · Celery calls http://fastapi:8001 · no DB)")),
    ("GET", "/health", "ai_service/main.py health()",
     T("200 {status: ok · degraded, model_loaded, classes, n_features, …}", "200 {status: ok · degraded, model_loaded, classes, n_features, …}"),
     T("⑤ (compose healthcheck)", "⑤ (compose healthcheck)")),
    ("POST", "/predict/video", T("routers/predictions.py predict_video() · multipart file", "routers/predictions.py predict_video() · multipart file"),
     T("200 predictions JSON · 400 확장자 · 빈 파일 · 413 100MB 초과 · 422 영상 못 읽음 · 503 모델 미준비", "200 predictions JSON · 400 extension · empty · 413 over 100MB · 422 unreadable · 503 model not ready"),
     "④ → ⑤ → ⑥ → ⑦ → ⑧ → ⑨"),
]
EP_COLS = [150, 300, 700, 1040, 0]     # 마지막 칸은 남은 폭
EP_RH, EP_GH = 33, 36


# ── 버튼 흐름: "AI 분석 시작" 1번 클릭이 지나는 파일 : 줄 → 함수 (40d3916 에서 줄 번호 확인) ──
FLOW_TITLE = T("버튼 흐름 · 「AI 분석 시작」 1번 클릭 → 파일 : 줄 → 함수 → 다음 함수 (원 번호 = 위 그림 노드 · 40d3916 기준)",
               "Button flow · one click on \"AI 분석 시작\" (Start analysis) → file : line → function → next function (circle = node above · at 40d3916)")
FLOW = [
    (1, "templates/analyses/index.html:65", "<button id=\"start-btn\">", T("form#analysis-form 전송", "submits form#analysis-form")),
    (1, "static/js/analyses.js:86", "submit → FormData (:88)", T("입력 방식 · 파일 · 카메라 번호", "input type · file · camera index")),
    (1, "static/js/analyses.js:100", "fetch(urls.list, POST)", T("X-CSRFToken · 세션 쿠키", "X-CSRFToken · session cookie")),
    (2, "config/urls.py:9", "path(\"api/v1/\", include)", T("API 주소는 여기 한 곳", "single API prefix")),
    (2, "config/api_urls.py:16", "include(analyses.api_urls)", T("app_name = \"api\"", "app_name = \"api\"")),
    (2, "analyses/api_urls.py:12", "router.register(\"analyses\")", T("DefaultRouter → ViewSet", "DefaultRouter → ViewSet")),
    (2, "analyses/views.py:71", "AnalysisJobViewSet.create()", T("IsAuthenticated 통과 후", "after IsAuthenticated")),
    (2, "analyses/serializers.py:47", "AnalysisJobCreateSerializer", T("validate_video_file :57 · validate :67", "validate_video_file :57 · validate :67")),
    (10, "analyses/views.py:75-76", "uuid4() → serializer.save()", T("AnalysisJob INSERT · PENDING", "AnalysisJob INSERT · PENDING")),
    (3, "analyses/views.py:79 → :36", "on_commit → enqueue_analysis()", T("apply_async :39 · 실패 → FAILURE 503 :86", "apply_async :39 · fails → FAILURE 503 :86")),
    (2, "analyses/views.py:96", "Response(202)", T("{id, task_id, status, status_url}", "{id, task_id, status, status_url}")),
    (4, "analyses/tasks.py:88", "run_analysis(job_id)", T("Redis 에서 꺼냄 → STARTED 저장", "taken from Redis → save STARTED")),
    (4, "analyses/tasks.py:106 → :34", "_prepare_video(job)", T("WEBCAM 이면 capture_clip() :44", "WEBCAM → capture_clip() :44")),
    (4, "analyses/services.py:19", "predict_video(path, job_id)", T("requests.post :26 · X-Job-ID 헤더", "requests.post :26 · X-Job-ID header")),
    (5, "ai_service/routers/predictions.py:33", "predict_video(request, file)", T("503 · 400 · 413 검사 → 임시 파일", "503 · 400 · 413 checks → temp file")),
    (6, "services/pose_pipeline.py:72", "PosePipeline.process_video()", T("predictions.py:56 · model.track() :82", "predictions.py:56 · model.track() :82")),
    (7, "src/multi_person_utils.py:11", "feature_from_keypoints(kp)", T("pose_pipeline.py:100 · 38-D", "pose_pipeline.py:100 · 38-D")),
    (8, "services/action_inference.py:60", "predict_tracks(model, tracks)", T("predictions.py:59 · 30 Step → 1,140 → RF", "predictions.py:59 · 30 steps → 1,140 → RF")),
    (9, "analyses/tasks.py:50", "save_result(job, data)", T("200 JSON · atomic :58 · bulk_create :60", "200 JSON · atomic :58 · bulk_create :60")),
    (11, "static/js/analyses.js:128 → views.py:119", "poll() → status()", T("2초마다 fetch :139 · Count 만", "fetch every 2 s :139 · Count only")),
    (12, "static/js/analyses.js:162", T("showResult() → 결과 표", "showResult() → result table"), T("상세 링크 #detail-link (index.html:81)", "detail link #detail-link (index.html:81)")),
]
FLOW_SUB = T("다른 버튼", "Other buttons")
FLOW_OTHER = [
    T("탭 (index.html:11·12) → analyses.js 입력 칸 전환만 (서버 요청 없음) · 노드 ①",
      "Tabs (index.html:11·12) → analyses.js switches input fields only (no request) · node ①"),
    T("미리보기 켜기 (index.html:46) → analyses.js:42·46 img.src → analyses/urls.py:12 → stream_views.py:57 camera_stream() → :65 requests.get → :78 StreamingHttpResponse (60초)",
      "Preview (index.html:46) → analyses.js:42·46 img.src → analyses/urls.py:12 → stream_views.py:57 camera_stream() → :65 requests.get → :78 StreamingHttpResponse (60 s)"),
    T("상세 결과 보기 (index.html:81 · 최근 기록) → analyses/urls.py:10 → page_views.py:28 detail() → models.py:28 visible_to() → ⑩ → detail.html",
      "Detail (index.html:81 · recent list) → analyses/urls.py:10 → page_views.py:28 detail() → models.py:28 visible_to() → ⑩ → detail.html"),
    T("대시보드 (base.html:17) → analyses/urls.py:11 → page_views.py:39 dashboard() (@staff_member_required) → :33 _count_by() ORM 집계 → Chart.js",
      "Dashboard (base.html:17) → analyses/urls.py:11 → page_views.py:39 dashboard() (@staff_member_required) → :33 _count_by() ORM aggregate → Chart.js"),
    T("가입 · 로그인 · 로그아웃 (base.html:21 POST) → accounts/urls.py:7·8·9 → views.signup :11 · LoginView · LogoutView → auth_user · django_session",
      "Sign up · log in · log out (base.html:21 POST) → accounts/urls.py:7·8·9 → views.signup :11 · LoginView · LogoutView → auth_user · django_session"),
    T("Admin (base.html:18) → config/urls.py:7 admin.site.urls → analyses/admin.py → ⑩",
      "Admin (base.html:18) → config/urls.py:7 admin.site.urls → analyses/admin.py → ⑩"),
]
FLOW_PER_ROW = 7
FLOW_CH, FLOW_VGAP = 104, 54

# ════════════════════════════════════════════════════════════════════
# 그리기
# ════════════════════════════════════════════════════════════════════
TOP_Y = 178
TOP_H = 54 + LH * max(len(c[2]) for c in top_cards)
NODE_Y = TOP_Y + TOP_H + 52
BOT_Y = NODE_Y + NODE_H + 52
BOT_H = 54 + LH * max(len(c[2]) for c in bot_cards)
LANE_Y = BOT_Y + BOT_H + 52
ROWB_Y = LANE_Y + 70
BC_Y = ROWB_Y + NODE_H + 52
BC_H = 54 + LH * max(len(c[2]) for c in b_cards)
SIDE_LH = 25
ROWD_Y = BC_Y + BC_H + 46
ROWD_H = 52 + SIDE_LH * len(side_compose[1])
FLOW_Y = ROWD_Y + ROWD_H + 40
FLOW_ROWS = -(-len(FLOW) // FLOW_PER_ROW)
FLOW_H = 70 + FLOW_ROWS * FLOW_CH + (FLOW_ROWS - 1) * FLOW_VGAP + 40 + 30 * len(FLOW_OTHER) + 4
EP_Y = FLOW_Y + FLOW_H + 40
EP_H = 60 + EP_RH + sum(EP_GH if r[0] == "group" else EP_RH for r in EP) + 14
H = EP_Y + EP_H + 96

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">')
add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
add(f'<text x="44" y="64" font-size="40" font-weight="700" fill="{INK}">{TITLE}</text>')
add(f'<text x="44" y="102" font-size="19" fill="{SUB}">{esc(SUBTITLE)}</text>')
for x1, x2, c, label in [(cx(0) - CARD_W / 2, cx(3) + CARD_W / 2, PURPLE, SEC_A),
                         (cx(4) - CARD_W / 2, cx(7) + CARD_W / 2, TEAL, SEC_B)]:
    add(f'<line x1="{x1}" y1="128" x2="{x2}" y2="128" stroke="{c}" stroke-width="5"/>')
    add(f'<text x="{x1}" y="158" font-size="19" font-weight="700" fill="{c}">{esc(label)}</text>')
    fit(label, 19, x2 - x1, "section", True)


def card(x, y, h, ic, title, lines, w=CARD_W):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.5"/>')
    add(icon(ic, x + 14, y + 17, 1.05))
    add(f'<text x="{x + 50}" y="{y + 33}" font-size="{F_CT}" font-weight="700" fill="{INK}">{esc(title)}</text>')
    fit(title, F_CT, w - 58, "card title", True)
    for k, t in enumerate(lines):
        add(f'<text x="{x + 50}" y="{y + 61 + k * LH}" font-size="{F_CL}" fill="{SUB}">{esc(t)}</text>')
        fit(t, F_CL, w - 60, "card")


def pill(xr, y, text):
    w = 16 + tw(text, 12.5, True)
    add(f'<rect x="{xr - w}" y="{y}" width="{w}" height="22" rx="11" fill="#F1F5F9" stroke="#CBD5E1" stroke-width="1"/>')
    add(f'<text x="{xr - w / 2}" y="{y + 16}" font-size="12.5" font-weight="700" fill="{SUB}" text-anchor="middle">{esc(text)}</text>')


def node(c, y, num, ic, title, role, f1, f2, color, tag=None):
    x = c - NODE_W / 2
    add(f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="12" fill="#fff" stroke="{color}" stroke-width="3"/>')
    add(icon(ic, c - 18, y + 30, 1.5, color, 1.9))
    add(f'<text x="{c}" y="{y + 98}" font-size="23" font-weight="700" fill="{INK}" text-anchor="middle">{esc(title)}</text>')
    add(f'<rect x="{x + 8}" y="{y + 110}" width="{NODE_W - 16}" height="25" rx="4" fill="#F1F5F9"/>')
    add(f'<text x="{c}" y="{y + 128}" font-size="14.5" font-weight="700" fill="{INK}" text-anchor="middle">{esc(role)}</text>')
    add(f'<text x="{c}" y="{y + 158}" font-size="14.5" fill="{SUB}" text-anchor="middle">{esc(f1)}</text>')
    add(f'<text x="{c}" y="{y + 181}" font-size="14.5" font-weight="700" fill="{color}" text-anchor="middle">{esc(f2)}</text>')
    fit(title, 23, NODE_W - 16, "node title", True); fit(role, 14.5, NODE_W - 20, "node role", True)
    fit(f1, 14.5, NODE_W - 12, "node f1"); fit(f2, 14.5, NODE_W - 12, "node f2", True)
    add(f'<circle cx="{x + 4}" cy="{y + 4}" r="18" fill="{color}"/>')
    add(f'<text x="{x + 4}" y="{y + 11}" font-size="{19 if num < 10 else 16}" font-weight="700" fill="#fff" text-anchor="middle">{num}</text>')
    if tag:
        pill(x + NODE_W - 8, y + 10, tag)


def harrow(x1, x2, y, above, below, color="#1E1B4B"):
    """x1 → x2 굵은 화살표 + 위(코드 · 데이터 형식) / 아래(쉬운 설명)"""
    d = 1 if x2 > x1 else -1
    add(f'<line x1="{x1}" y1="{y}" x2="{x2 - d * 20}" y2="{y}" stroke="{color}" stroke-width="5"/>')
    add(f'<path d="M{x2 - d * 24} {y - 15} L{x2} {y} L{x2 - d * 24} {y + 15} Z" fill="{color}"/>')
    m = (x1 + x2) / 2
    gap = abs(x2 - x1) + 30
    for k, t in enumerate(above):
        add(f'<text x="{m}" y="{y - 26 - (len(above) - 1 - k) * 18}" font-size="14.5" font-weight="700" fill="{INK}" text-anchor="middle">{esc(t)}</text>')
        fit(t, 14.5, gap, "arrow above", True)
    for k, t in enumerate(below):
        add(f'<text x="{m}" y="{y + 38 + k * 18}" font-size="14" fill="{SUB}" text-anchor="middle">{esc(t)}</text>')
        fit(t, 14, gap, "arrow below")


def side_box(x1, x2, y, ic, color, fill, title, lines, dashed=False, h=None):
    dash = ' stroke-dasharray="8 6"' if dashed else ""
    h = h or 52 + SIDE_LH * len(lines)
    add(f'<rect x="{x1}" y="{y}" width="{x2 - x1}" height="{h}" rx="10" fill="{fill}" stroke="{color}" stroke-width="{2 if dashed else 2.2}"{dash}/>')
    add(icon(ic, x1 + 18, y + 18, 1.2, color, 1.9))
    add(f'<text x="{x1 + 62}" y="{y + 36}" font-size="18.5" font-weight="700" fill="{INK}">{esc(title)}</text>')
    fit(title, 18.5, x2 - x1 - 70, "side title", True)
    for k, t in enumerate(lines):
        add(f'<text x="{x1 + 62}" y="{y + 64 + SIDE_LH * k}" font-size="15" fill="{SUB}">{esc(t)}</text>')
        fit(t, 15, x2 - x1 - 74, "side")
    return h


# ── 위 줄: 요청이 가는 길 ──
for i in range(8):
    c = cx(i)
    add(f'<line x1="{c}" y1="{TOP_Y + TOP_H}" x2="{c}" y2="{NODE_Y}" stroke="{LINE}" stroke-width="2" stroke-dasharray="6 6"/>')
    add(f'<line x1="{c}" y1="{NODE_Y + NODE_H}" x2="{c}" y2="{BOT_Y}" stroke="{LINE}" stroke-width="2" stroke-dasharray="6 6"/>')
    card(c - CARD_W / 2, TOP_Y, TOP_H, *top_cards[i])
    card(c - CARD_W / 2, BOT_Y, BOT_H, *bot_cards[i])
ay = NODE_Y + NODE_H / 2 + 6
for i in range(7):
    harrow(cx(i) + NODE_W / 2 + 2, cx(i + 1) - NODE_W / 2 - 2, ay, *arrows_a[i])
for i, n in enumerate(nodes_a):
    node(cx(i), NODE_Y, i + 1, *n)

# ── 8 → 9: 추론 결과가 Celery 로 돌아옴 ──
x8, x9 = cx(7), cx(3)
add(f'<path d="M{x8} {BOT_Y + BOT_H} V{LANE_Y} H{x9 + 44} V{ROWB_Y - 20}" fill="none" stroke="{TEAL}" stroke-width="4.5"/>')
add(f'<path d="M{x9 + 29} {ROWB_Y - 24} L{x9 + 44} {ROWB_Y} L{x9 + 59} {ROWB_Y - 24} Z" fill="{TEAL}"/>')
lx = (x8 + x9) / 2 + 22
lw = tw(LANE_LABEL, 16, True) + 24
add(f'<rect x="{lx - lw / 2}" y="{LANE_Y - 15}" width="{lw}" height="30" fill="#fff"/>')
add(f'<text x="{lx}" y="{LANE_Y + 6}" font-size="16" font-weight="700" fill="{TEAL}" text-anchor="middle">{esc(LANE_LABEL)}</text>')
add(f'<text x="{lx}" y="{LANE_Y + 32}" font-size="14.5" fill="{SUB}" text-anchor="middle">{esc(LANE_SUB)}</text>')
fit(LANE_LABEL, 16, x8 - x9 - 60, "lane", True)

# ── 아래 줄: 저장 → 조회 → 화면 (오른쪽 → 왼쪽) ──
by = ROWB_Y + NODE_H / 2 + 6
for k in range(3):
    ci = nodes_b[k][0]
    harrow(cx(ci) - NODE_W / 2 - 2, cx(ci - 1) + NODE_W / 2 + 2, by, *arrows_b[k])
for k, (ci, num, *rest) in enumerate(nodes_b):
    node(cx(ci), ROWB_Y, num, *rest)
    add(f'<line x1="{cx(ci)}" y1="{ROWB_Y + NODE_H}" x2="{cx(ci)}" y2="{BC_Y}" stroke="{LINE}" stroke-width="2" stroke-dasharray="6 6"/>')
    card(cx(ci) - CARD_W / 2, BC_Y, BC_H, *b_cards[k])

# ── 파란 점선: Django ORM 으로 PostgreSQL 에 쓰는 지점 ──
gx = cx(1) + CARD_W / 2 + 11
add(f'<path d="M{cx(1) + NODE_W / 2} {NODE_Y + NODE_H - 28} H{gx} V{ROWB_Y - 30} H{cx(2) - 44} V{ROWB_Y - 4}" fill="none" stroke="{BLUE}" stroke-width="2.6" stroke-dasharray="8 6"/>')
add(f'<path d="M{cx(2) - 55} {ROWB_Y - 18} L{cx(2) - 44} {ROWB_Y} L{cx(2) - 33} {ROWB_Y - 18} Z" fill="{BLUE}"/>')
add(f'<text x="{gx - 10}" y="{ROWB_Y - 40}" font-size="14.5" font-weight="700" fill="{BLUE}" text-anchor="end">{esc(LBL_PENDING)}</text>')
gx3 = cx(3) - CARD_W / 2 - 11
add(f'<path d="M{cx(3) - 44} {NODE_Y + NODE_H} V{NODE_Y + NODE_H + 20} H{gx3} V{ROWB_Y - 52} H{cx(2) + 44} V{ROWB_Y - 4}" fill="none" stroke="{BLUE}" stroke-width="2.6" stroke-dasharray="8 6"/>')
add(f'<path d="M{cx(2) + 33} {ROWB_Y - 18} L{cx(2) + 44} {ROWB_Y} L{cx(2) + 55} {ROWB_Y - 18} Z" fill="{BLUE}"/>')
add(f'<text x="{cx(2) + 56}" y="{ROWB_Y - 62}" font-size="14.5" font-weight="700" fill="{BLUE}">{esc(LBL_STARTED)}</text>')

# ── 오른쪽: 관리자 · 웹캠 / 회원 · 헬스체크 ──
LX1, LX2 = cx(4) - CARD_W / 2, cx(5) + CARD_W / 2
RX1, RX2 = cx(6) - CARD_W / 2, cx(7) + CARD_W / 2
top_h = 52 + SIDE_LH * 6
side_y = ROWB_Y - 14
side_box(LX1, LX2, side_y, "chart", GRAY, "#F8FAFC", *side_admin, h=top_h)
side_box(RX1, RX2, side_y, "camera", PURPLE, "#FAF5FF", *side_cam, h=top_h)
y2 = side_y + top_h + 18
h2 = BC_Y + BC_H - y2
side_box(LX1, LX2, y2, "user", PURPLE, "#FAF5FF", *side_acc, h=h2)
side_box(RX1, RX2, y2, "heart", PURPLE, "#FAF5FF", *side_health, h=h2)

# PostgreSQL(10) → 관리자 화면 : ORM 집계 읽기
ry = ROWB_Y + NODE_H + 26
ay2 = side_y + top_h - 40
add(f'<path d="M{cx(2) + 70} {ROWB_Y + NODE_H} V{ry} H{LX1 - 36} V{ay2} H{LX1 - 18}" fill="none" stroke="{GRAY}" stroke-width="3.2"/>')
add(f'<path d="M{LX1 - 20} {ay2 - 11} L{LX1} {ay2} L{LX1 - 20} {ay2 + 11} Z" fill="{GRAY}"/>')
lw = tw(LBL_ADMIN, 14.5, True) + 16
add(f'<rect x="{cx(2) + 82}" y="{ry - 11}" width="{lw}" height="22" fill="#fff"/>')
add(f'<text x="{cx(2) + 90}" y="{ry + 5}" font-size="14.5" font-weight="700" fill="{INK}">{esc(LBL_ADMIN)}</text>')

# ── 맨 아래: compose · 검증 · GitHub ──
side_box(cx(0) - CARD_W / 2, cx(3) + CARD_W / 2, ROWD_Y, "box", BLUE, "#EFF6FF", *side_compose, h=ROWD_H)
side_box(LX1, LX2, ROWD_Y, "check", "#94A3B8", "#F8FAFC", *side_tests, dashed=True, h=ROWD_H)
side_box(RX1, RX2, ROWD_Y, "branch", PURPLE, "#FAF5FF", *side_git, dashed=True, h=ROWD_H)



# ── 버튼 흐름 (지그재그: 1줄 → , 2줄 ← , 3줄 →) ──
fx1, fx2 = cx(0) - CARD_W / 2, cx(7) + CARD_W / 2
add(f'<rect x="{fx1}" y="{FLOW_Y}" width="{fx2 - fx1}" height="{FLOW_H}" rx="10" fill="#fff" stroke="{PURPLE}" stroke-width="2.4"/>')
add(icon("route", fx1 + 18, FLOW_Y + 18, 1.2, PURPLE, 1.9))
add(f'<text x="{fx1 + 62}" y="{FLOW_Y + 38}" font-size="19" font-weight="700" fill="{INK}">{esc(FLOW_TITLE)}</text>')
fit(FLOW_TITLE, 19, fx2 - fx1 - 80, "flow title", True)
FGAP = 46
FCW = (fx2 - fx1 - 40 - FGAP * (FLOW_PER_ROW - 1)) / FLOW_PER_ROW
NCOL = {1: PURPLE, 2: PURPLE, 3: PURPLE, 4: PURPLE, 5: TEAL, 6: BLUE, 7: TEAL, 8: TEAL, 9: PURPLE, 10: BLUE, 11: PURPLE, 12: PURPLE}
CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫"
pos = []
for k, (num, fl, fn, note) in enumerate(FLOW):
    r, c = divmod(k, FLOW_PER_ROW)
    if r % 2 == 1:
        c = FLOW_PER_ROW - 1 - c
    x = fx1 + 20 + c * (FCW + FGAP)
    y = FLOW_Y + 70 + r * (FLOW_CH + FLOW_VGAP)
    pos.append((x, y, r))
    col = NCOL[num]
    add(f'<rect x="{x}" y="{y}" width="{FCW}" height="{FLOW_CH}" rx="8" fill="#F8FAFC" stroke="{col}" stroke-width="2"/>')
    add(f'<circle cx="{x + 20}" cy="{y + 22}" r="14" fill="{col}"/>')
    add(f'<text x="{x + 20}" y="{y + 27.5}" font-size="{14 if num < 10 else 12}" font-weight="700" fill="#fff" text-anchor="middle">{num}</text>')
    add(f'<text x="{x + 40}" y="{y + 27}" font-size="13.5" font-weight="700" fill="{SUB}">{esc(fl)}</text>')
    add(f'<text x="{x + 14}" y="{y + 58}" font-size="16.5" font-weight="700" fill="{INK}">{esc(fn)}</text>')
    add(f'<text x="{x + 14}" y="{y + 86}" font-size="14" fill="{SUB}">{esc(note)}</text>')
    fit(fl, 13.5, FCW - 48, "flow file", True); fit(fn, 16.5, FCW - 22, "flow fn", True); fit(note, 14, FCW - 22, "flow note")
for k in range(len(FLOW) - 1):
    x, y, r = pos[k]
    x2_, y2_, r2 = pos[k + 1]
    if r == r2:
        if x2_ > x:
            a1, a2 = x + FCW + 3, x2_ - 3
        else:
            a1, a2 = x - 3, x2_ + FCW + 3
        d = 1 if a2 > a1 else -1
        ym = y + FLOW_CH / 2
        add(f'<line x1="{a1}" y1="{ym}" x2="{a2 - d * 14}" y2="{ym}" stroke="#1E1B4B" stroke-width="3.5"/>')
        add(f'<path d="M{a2 - d * 16} {ym - 10} L{a2} {ym} L{a2 - d * 16} {ym + 10} Z" fill="#1E1B4B"/>')
    else:
        xm = x + FCW / 2
        add(f'<line x1="{xm}" y1="{y + FLOW_CH + 3}" x2="{xm}" y2="{y2_ - 16}" stroke="#1E1B4B" stroke-width="3.5"/>')
        add(f'<path d="M{xm - 10} {y2_ - 18} L{xm} {y2_ - 2} L{xm + 10} {y2_ - 18} Z" fill="#1E1B4B"/>')
oy = FLOW_Y + 70 + FLOW_ROWS * FLOW_CH + (FLOW_ROWS - 1) * FLOW_VGAP + 40
add(f'<line x1="{fx1 + 20}" y1="{oy - 16}" x2="{fx2 - 20}" y2="{oy - 16}" stroke="#E2E8F0" stroke-width="1.5"/>')
add(f'<text x="{fx1 + 20}" y="{oy + 14}" font-size="17" font-weight="700" fill="{PURPLE}">{esc(FLOW_SUB)}</text>')
for k, t in enumerate(FLOW_OTHER):
    add(f'<text x="{fx1 + 150}" y="{oy + 14 + 30 * k}" font-size="15.5" fill="{SUB}">· {esc(t)}</text>')
    fit(t, 15.5, fx2 - fx1 - 180, "flow other")

# ── 주소(엔드포인트) 표 ──
MCOL = {"GET": "#15803D", "POST": "#1D4ED8", "PATCH": "#B45309", "DELETE": "#B91C1C"}
tx1, tx2 = cx(0) - CARD_W / 2, cx(7) + CARD_W / 2
add(f'<rect x="{tx1}" y="{EP_Y}" width="{tx2 - tx1}" height="{EP_H}" rx="10" fill="#fff" stroke="{GRAY}" stroke-width="2.2"/>')
add(icon("route", tx1 + 18, EP_Y + 18, 1.2, GRAY, 1.9))
add(f'<text x="{tx1 + 62}" y="{EP_Y + 38}" font-size="19" font-weight="700" fill="{INK}">{esc(EP_TITLE)}</text>')
xs = [tx1 + 20]
for wcol in EP_COLS[:-1]:
    xs.append(xs[-1] + wcol)
widths = [EP_COLS[i] if EP_COLS[i] else tx2 - 20 - xs[i] for i in range(5)]
yy = EP_Y + 60
add(f'<rect x="{tx1 + 12}" y="{yy}" width="{tx2 - tx1 - 24}" height="{EP_RH}" fill="#E2E8F0"/>')
for i, hname in enumerate(EP_HEAD):
    add(f'<text x="{xs[i] + 8}" y="{yy + 22}" font-size="15" font-weight="700" fill="{INK}">{esc(hname)}</text>')
yy += EP_RH
alt = False
for r in EP:
    if r[0] == "group":
        add(f'<rect x="{tx1 + 12}" y="{yy}" width="{tx2 - tx1 - 24}" height="{EP_GH}" fill="#F1F5F9"/>')
        add(f'<text x="{xs[0] + 8}" y="{yy + 24}" font-size="15.5" font-weight="700" fill="{PURPLE}">{esc(r[1])}</text>')
        yy += EP_GH
        alt = False
        continue
    if alt:
        add(f'<rect x="{tx1 + 12}" y="{yy}" width="{tx2 - tx1 - 24}" height="{EP_RH}" fill="#F8FAFC"/>')
    alt = not alt
    mx = xs[0] + 8
    for m in r[0].split():
        mw = 12 + tw(m, 12.5, True)
        add(f'<rect x="{mx}" y="{yy + 7}" width="{mw}" height="20" rx="4" fill="{MCOL[m]}"/>')
        add(f'<text x="{mx + mw / 2}" y="{yy + 21.5}" font-size="12.5" font-weight="700" fill="#fff" text-anchor="middle">{m}</text>')
        mx += mw + 6
    for i, t in enumerate(r[1:], start=1):
        weight = ' font-weight="700"' if i in (1, 4) else ""
        color = INK if i in (1, 4) else SUB
        add(f'<text x="{xs[i] + 8}" y="{yy + 22}" font-size="15"{weight} fill="{color}">{esc(t)}</text>')
        fit(t, 15, widths[i] - 14, f"ep col{i}", i in (1, 4))
    add(f'<line x1="{tx1 + 12}" y1="{yy + EP_RH}" x2="{tx2 - 12}" y2="{yy + EP_RH}" stroke="#E2E8F0" stroke-width="1"/>')
    yy += EP_RH
for xv in xs[1:]:
    add(f'<line x1="{xv}" y1="{EP_Y + 60}" x2="{xv}" y2="{yy}" stroke="#E2E8F0" stroke-width="1"/>')

add(f'<text x="44" y="{H - 40}" font-size="16" fill="{SUB}">{esc(LEGEND)}</text>')
fit(LEGEND, 16, W - 80, "legend")
add('</svg>')

name = "architecture.svg" if LANG == "ko" else "architecture.en.svg"
Path(__file__).with_name(name).write_text("\n".join(out), encoding="utf-8")
print(name, W, H)
for w in WARN:
    print("  overflow?", w)
