"""Vision Action Platform 파이프라인 (yolo-pose-action-recognition-project 흐름도 방식, 개발자용 v5)
기준: GitHub main 40d3916 실제 파일만. 코드에 없는 것(CSV 등)은 그리지 않는다.
python3 make_pipeline.py        ->  pipeline.svg     (한국어)
python3 make_pipeline.py en     ->  pipeline.en.svg  (영어, translate_pipeline_en.py 가 부름)
"""
import sys
from pathlib import Path

LANG = sys.argv[1] if len(sys.argv) > 1 else "ko"


def T(ko, en=None):
    return en if (LANG == "en" and en is not None) else ko


W = 1600
FONT = "Noto Sans CJK KR, Malgun Gothic, sans-serif"
INK, SUB, MUTED, RED = "#0F172A", "#475569", "#64748B", "#DC2626"
STYLE = {
    "cfg": ("#3B82F6", "#EFF6FF"),   # 설정 · 직접 작성 파일
    "vid": ("#06B6D4", "#ECFEFF"),   # 영상 · 미디어
    "py": ("#334155", "#FFFFFF"),    # Python · JS 처리
    "dat": ("#22C55E", "#F0FDF4"),   # 실행 중 만들어지는 데이터
    "mdl": ("#8B5CF6", "#F5F3FF"),   # 학습 모델 파일
    "out": ("#F59E0B", "#FFFBEB"),   # 결과 · 저장 · 응답
    "test": ("#94A3B8", "#F8FAFC"),  # 검증 (실행 순서 아님)
}
BW = 430
COL = {"L": 40, "M": 585, "R": 1130}
F_T, F_L, LH = 15.5, 13, 19       # 상자 제목 · 글자 · 줄 간격
F_A = 12                           # 화살표 글자
WARN = []


def tw(s, size, bold=False):
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


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


out = []
body = []
add = body.append


def box(col, y, kind, title, role=None, lines=(), label=False, tag=None):
    x = COL[col]
    n = len(lines) + (1 if role else 0)
    h = 40 + LH * n + (6 if n else 0)
    stroke, fill = STYLE[kind]
    dash = ' stroke-dasharray="7 5"' if kind == "test" else ""
    add(f'<rect x="{x}" y="{y}" width="{BW}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="{2.2 if kind == "py" else 2}"{dash}/>')
    if kind != "test":
        add(f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="2" fill="{stroke}"/>')
    add(f'<text x="{x + 18}" y="{y + 26}" font-size="{F_T}" font-weight="700" fill="{INK}">{esc(title)}</text>')
    fit(title, F_T, BW - 30 - (tw(tag, 11.5, True) + 24 if tag else 0) - (100 if label else 0), "title", True)
    k0 = 0
    if role:
        rt = T("역할 · ", "role · ") + role
        w = 14 + tw(rt, 12, True)
        add(f'<rect x="{x + 14}" y="{y + 36}" width="{w}" height="19" rx="3" fill="{stroke}" fill-opacity="0.13"/>')
        add(f'<text x="{x + 21}" y="{y + 50}" font-size="12" font-weight="700" fill="{INK}">{esc(rt)}</text>')
        k0 = 1
    for k, t in enumerate(lines):
        add(f'<text x="{x + 18}" y="{y + 50 + LH * (k + k0)}" font-size="{F_L}" fill="{SUB}">{esc(t)}</text>')
        fit(t, F_L, BW - 28, "line")
    if label:
        add(f'<rect x="{x + BW - 112}" y="{y - 10}" width="102" height="20" rx="10" fill="#fff" stroke="{RED}" stroke-width="1.4"/>')
        add(f'<circle cx="{x + BW - 99}" cy="{y}" r="3.8" fill="{RED}"/>')
        add(f'<text x="{x + BW - 90}" y="{y + 4.5}" font-size="12" font-weight="700" fill="{RED}">action_label</text>')
    if tag:
        w = 14 + tw(tag, 11.5, True)
        add(f'<rect x="{x + BW - w - 10}" y="{y + 10}" width="{w}" height="20" rx="10" fill="#F1F5F9" stroke="#CBD5E1"/>')
        add(f'<text x="{x + BW - 10 - w / 2}" y="{y + 24.5}" font-size="11.5" font-weight="700" fill="{SUB}" text-anchor="middle">{esc(tag)}</text>')
    return {"x1": x, "y1": y, "x2": x + BW, "y2": y + h, "cx": x + BW / 2, "cy": y + h / 2}


ARROWS = []


def arrow(d, kind="dark", label=None, at=None):
    ARROWS.append((d, kind, label, at))


def draw_arrows():
    for d, kind, label, at in ARROWS:
        color, dash, mk = {"dark": ("#334155", "", "ar"), "gray": ("#94A3B8", ' stroke-dasharray="6 4"', "arg")}[kind]
        add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.8"{dash} marker-end="url(#{mk})"/>')
        if label:
            lx, ly = at
            w = tw(label, F_A) + 14
            add(f'<rect x="{lx - w / 2}" y="{ly - 12}" width="{w}" height="17" rx="3" fill="#fff"/>')
            add(f'<text x="{lx}" y="{ly + 1.5}" font-size="{F_A}" fill="{MUTED if kind == "dark" else "#64748B"}" text-anchor="middle">{esc(label)}</text>')


PANELS = []


def panel(y1, y2, title, sub, dashed=False):
    PANELS.append((y1, y2, title, sub, dashed))


def down(a, b, label=None):
    arrow(f"M{a['cx']} {a['y2']} V{b['y1'] - 2}", label=label, at=(a["cx"], a["y2"] + 17) if label else None)


def right(a, b, label=None, kind="dark"):
    y = (max(a["y1"], b["y1"]) + min(a["y2"], b["y2"])) / 2
    arrow(f"M{a['x2']} {y} H{b['x1'] - 2}", kind, label, ((a["x2"] + b["x1"]) / 2, y - 9) if label else None)


def left(a, b, label=None, kind="dark"):
    y = (max(a["y1"], b["y1"]) + min(a["y2"], b["y2"])) / 2
    arrow(f"M{a['x1']} {y} H{b['x2'] + 2}", kind, label, ((a["x1"] + b["x2"]) / 2, y - 9) if label else None)


GAP = 42
P_HEAD = 66          # 패널 제목 높이

# ════════════════════════ ① 설정 · 모델 파일 ════════════════════════
y = 156
pj = box("L", y, "cfg", "ai_service/project.json", T("Pose · Window · 추적 설정값", "pose · window · tracking settings"), [
    "pose_model yolo11n-pose.pt · image_size 640",
    "person_confidence 0.25 · keypoint_confidence 0.5",
    "day06_baseline: sequence_steps 30 · min_valid_frames 10",
    T("day07_realtime: window 5.0초 · 간격 0.25초 · 0.55", "day07_realtime: window 5.0 s · every 0.25 s · 0.55"),
    T("  fill 0.8 · valid 0.6 · min 10 · 안정화 5표 중 3", "  fill 0.8 · valid 0.6 · min 10 · 3 of 5 votes"),
    T("day08_multi_person: bytetrack.yaml · lost 2.0초", "day08_multi_person: bytetrack.yaml · lost 2.0 s"),
    T("읽는 곳 → model_loader.load_project_config()", "read by → model_loader.load_project_config()")])
md = box("M", y, "mdl", "ai_service/models/", T("학습된 모델 · Pose 가중치", "trained model · pose weights"), [
    T("rf_action_baseline.joblib   RandomForest (Git 제외)", "rf_action_baseline.joblib   RandomForest (not in Git)"),
    T("rf_feature_columns.json   1,140 컬럼 이름 · 순서", "rf_feature_columns.json   1,140 column names · order"),
    "      t00_nose_x … t29_right_knee_angle",
    T("rf_training_info.json   steps 30 · 6 class · 300 trees", "rf_training_info.json   steps 30 · 6 classes · 300 trees"),
    T("yolo11n-pose.pt   YOLO Pose 가중치 (Git 제외)", "yolo11n-pose.pt   YOLO Pose weights (not in Git)"),
    T("읽는 곳 → load_action_model() · PosePipeline()", "read by → load_action_model() · PosePipeline()")], label=True)
env = box("R", y, "cfg", T(".env  (← .env.example 복사)", ".env  (copy of .env.example)"), T("서비스 주소 · 파일명 · 제한값", "addresses · file names · limits"), [
    "MODEL_DIR=/app/models · POSE_DEVICE=cpu",
    "RF_MODEL_FILE · RF_COLUMNS_FILE · RF_INFO_FILE",
    "CELERY_BROKER_URL=redis://redis:6379/0",
    "AI_SERVICE_URL=http://fastapi:8001 · TIMEOUT 300",
    "MAX_UPLOAD_MB=100 · LOW_CONFIDENCE_THRESHOLD=0.55",
    "IP_WEBCAM_ALLOWED_URLS · CAMERA_CAPTURE_SECONDS=8",
    T("읽는 곳 → config/settings.py · model_loader", "read by → config/settings.py · model_loader")])
y = max(pj["y2"], md["y2"], env["y2"]) + 26
cmp = box("R", y, "cfg", "compose.yaml", T("5개 서비스 · 포트 · 볼륨", "5 services · ports · volumes"), [
    T("postgres · redis · fastapi · django · celery (5개)", "postgres · redis · fastapi · django · celery (5)"),
    T("fastapi 127.0.0.1:8001 · django 8000:8000 (나머지 내부)", "fastapi 127.0.0.1:8001 · django 8000:8000 (rest internal)"),
    T("볼륨 postgres_data · media_data · ./ai_service/models (ro)", "volumes postgres_data · media_data · models (ro)"),
    T("healthcheck → depends_on service_healthy 순서", "healthcheck → depends_on service_healthy order"),
    "env_file: .env · TZ=Asia/Seoul"])
mnt = box("M", y, "vid", T("/app/models  (fastapi 컨테이너 안)", "/app/models  (inside fastapi)"), T("읽기 전용 마운트", "read-only mount"), [
    T("compose: ./ai_service/models:/app/models:ro", "compose: ./ai_service/models:/app/models:ro"),
    T("이미지에 굽지 않음 → 모델만 바꿔 끼울 수 있음", "not baked into the image → swap the model only")])
down(md, mnt, T("마운트", "mount"))
left(cmp, mnt)
p1_end = max(cmp["y2"], mnt["y2"]) + 24
panel(100, p1_end, T("① 설정 · 모델 파일 — 무엇을 읽는가", "① Settings · model files — what is read"),
      T("레포에 있는 설정 + Git 에 올리지 않는 모델 2개 (README '모델 준비' 대로 ai_service/models/ 에 복사) · 각 상자 마지막 줄 = 읽는 곳",
        "settings in the repo + 2 model files kept out of Git (copy into ai_service/models/ as in the README) · last line of each box = who reads it"))

# ════════════════════════ ② 서버 시작 ════════════════════════
y = p1_end + 18 + P_HEAD
lpc = box("L", y, "py", "load_project_config()", T("설정 파일 읽기", "read settings"),
          ["services/model_loader.py", T("project.json → dict (없으면 ModelNotReady)", "project.json → dict (missing → ModelNotReady)")])
lam = box("M", y, "py", "load_action_model()", T("모델 로드 + 규격 확인", "load model + check spec"), [
    T("services/model_loader.py · 파일명 = .env RF_*_FILE", "services/model_loader.py · names = .env RF_*_FILE"),
    "joblib.load · json.loads × 2",
    T("검사 ① n_features_in_ = 컬럼 수 = 1,140", "check ① n_features_in_ = columns = 1,140"),
    T("검사 ② 1,140 % sequence_steps(30) = 0", "check ② 1,140 % sequence_steps(30) = 0"),
    T("검사 ③ 컬럼 = sequence_feature_names(30)", "check ③ columns = sequence_feature_names(30)"),
    T("검사 ④ model.classes_ = 6개 Action", "check ④ model.classes_ = 6 actions"),
    T("→ ActionModel(model, classes, 30, 38, 1140)", "→ ActionModel(model, classes, 30, 38, 1140)")], label=True)
pp = box("R", y, "py", "PosePipeline(config)", T("YOLO Pose 준비", "prepare YOLO Pose"), [
    "services/pose_pipeline.py",
    "YOLO(/app/models/yolo11n-pose.pt)",
    "imgsz 640 · conf 0.25 · device cpu",
    "tracker bytetrack.yaml · MAX_VIDEO_SECONDS 60",
    T("threading.Lock: 영상 1건씩 순서대로", "threading.Lock: one video at a time")])
down(pj, lpc, T("설정 읽기", "read")); down(mnt, lam, T("joblib · json 로드", "load joblib · json"))
arrow(f"M{mnt['x2'] - 40} {mnt['y2']} V{cmp['y2'] + 14} H{pp['cx'] + 80} V{pp['y1'] - 2}", label="yolo11n-pose.pt", at=(pp["cx"] + 80, pp["y1"] - 22))
y = max(lam["y2"], pp["y2"]) + GAP
st = box("M", y, "dat", T("app.state  (main.py lifespan · 시작 시 1번)", "app.state  (main.py lifespan · once)"), T("요청마다 재사용할 객체", "objects reused per request"), [
    "config · action_model (ActionModel) · pose (PosePipeline)",
    T("실패해도 서버는 뜸 → load_error 에 원인 저장", "server still starts → reason kept in load_error")])
hl = box("R", y, "out", "GET /health  (fastapi)", T("서버 · 모델 상태", "server · model status"), [
    "{status, model_loaded, classes, n_features,",
    " sequence_steps, feature_dim, pose_model, error}",
    T("실패 → degraded · /predict/video 503", "failure → degraded · /predict/video 503")])
down(lam, st, "ActionModel")
arrow(f"M{lpc['cx']} {lpc['y2']} V{st['cy']} H{st['x1'] - 2}", label="config (dict)", at=(lpc["cx"], st["cy"] - 30))
arrow(f"M{pp['cx'] + 80} {pp['y2']} V{hl['y1'] - 2}")
arrow(f"M{pp['x1'] + 30} {pp['y2']} V{pp['y2'] + 20} H{st['x2'] - 60} V{st['y1'] - 2}", label="pose", at=(pp["x1"] - 12, pp["y2"] + 16))
p2_end = max(st["y2"], hl["y2"]) + 24
panel(p1_end + 18, p2_end, T("② 서버 시작 — ai_service/main.py lifespan", "② Server start — ai_service/main.py lifespan"),
      T("요청이 오기 전에 설정 · 모델 · Pose 를 한 번 로드하고 규격(1,140 · 30 Step · 6 Class · 컬럼 순서)을 검사", "load settings · model · pose once before any request and check the spec (1,140 · 30 steps · 6 classes · column order)"))

# ════════════════════════ ③ 입력 영상 확보 ════════════════════════
y = p2_end + 18 + P_HEAD
acc = box("L", y, "py", T("accounts/  · 로그인 화면", "accounts/  · login pages"), T("로그인 · 회원가입", "login · signup"), [
    "/accounts/login/ → LoginView · /signup/ → views.signup",
    T("/accounts/logout/ → LogoutView (POST 만)", "/accounts/logout/ → LogoutView (POST only)"),
    T("성공 → 세션 쿠키 · LOGIN_REDIRECT_URL = 분석 화면", "success → session cookie · redirect to index"),
    "GET /api/v1/auth/me/ → MeSerializer"])
idx = box("M", y, "cfg", "page_views.index → index.html", T("분석 화면 HTML", "analysis page HTML"), [
    T("GET / → config/urls.py → analyses/urls.py", "GET / → config/urls.py → analyses/urls.py"),
    T("@login_required (미로그인 → /accounts/login/)", "@login_required (else → /accounts/login/)"),
    T("data-list-url · data-status-url = {% url 'api:...' %}", "data-list-url · data-status-url = {% url 'api:...' %}"),
    T("허용 카메라 번호 · 확장자 · 100MB · 600초 전달", "camera numbers · extensions · 100MB · 600 s")])
right(acc, idx, T("세션", "session"))
y = max(acc["y2"], idx["y2"]) + GAP
url = box("L", y, "cfg", T("주소 따라가기 (API)", "Follow the URL (API)"), T("URL → 함수 연결", "URL → function"), [
    'config/urls.py path("api/v1/", namespace="api")',
    "→ config/api_urls.py (app_name=\"api\")",
    "→ analyses/api_urls.py DefaultRouter",
    '   router.register("analyses", AnalysisJobViewSet)',
    "→ POST analyses/ = AnalysisJobViewSet.create()"])
js = box("M", y, "py", "static/js/analyses.js", T("요청 보내고 상태 폴링", "send request · poll status"), [
    T("탭 UPLOAD / WEBCAM → input_type", "tab UPLOAD / WEBCAM → input_type"),
    T("submit → fetch POST /api/v1/analyses/", "submit → fetch POST /api/v1/analyses/"),
    "body FormData · headers X-CSRFToken",
    T("res.status !== 202 → 오류 문구 표시", "res.status !== 202 → show error")])
pvw = box("R", y, "vid", "stream_views.camera_stream", T("웹캠 실시간 미리보기", "webcam live preview"), [
    T("GET /cameras/<index>/stream/ · @login_required", "GET /cameras/<index>/stream/ · @login_required"),
    T("허용 목록 밖 → 404 · 카메라 실패 → 502", "not allowed → 404 · camera down → 502"),
    T("MJPEG 바이트 그대로 중계 · 최대 60초", "relays MJPEG bytes · max 60 s"),
    T("카메라 IP 는 화면에 안 보임 · 분석과 별도", "camera IP hidden · separate from analysis")], tag="django")
down(idx, js, T("<script> (WhiteNoise)", "<script> (WhiteNoise)"))
right(js, pvw, T("WEBCAM 탭", "WEBCAM tab"))
y = max(url["y2"], js["y2"], pvw["y2"]) + GAP
ser = box("L", y, "py", "serializers.AnalysisJobCreateSerializer", T("입력값 검사", "validate input"), [
    T("validate_video_file: mp4 · mov · avi · mkv · 100MB", "validate_video_file: mp4 · mov · avi · mkv · 100MB"),
    T("UPLOAD → video_file 필수", "UPLOAD → video_file required"),
    T("WEBCAM → camera_index < 허용 목록 길이", "WEBCAM → camera_index < allow-list length"),
    "  capture_seconds = CAMERA_CAPTURE_SECONDS(8)",
    T("틀리면 400 {필드: 메시지}", "invalid → 400 {field: message}")])
vw = box("M", y, "py", "views.AnalysisJobViewSet.create()", T("요청 접수 · 작업 저장 · 큐 등록", "accept · save job · enqueue"), [
    "① SessionAuthentication · IsAuthenticated",
    T("② serializer.is_valid(raise_exception=True)", "② serializer.is_valid(raise_exception=True)"),
    "③ task_id = str(uuid.uuid4())",
    "   save(user, celery_task_id=task_id)",
    T("   → AnalysisJob 1행 PENDING · 영상 → media/videos/", "   → 1 AnalysisJob row PENDING · video → media/videos/"),
    "④ transaction.on_commit(enqueue_analysis)",
    T("   → run_analysis.apply_async(args=[pk], task_id)", "   → run_analysis.apply_async(args=[pk], task_id)")])
r202 = box("R", y, "out", T("202 JSON → analyses.js", "202 JSON → analyses.js"), T("작업 ID 바로 반환", "returns job id right away"), [
    '{id, task_id, status: "PENDING",',
    ' status_url: reverse("api:analysis-status")}',
    T("Redis 등록 실패 → FAILURE 저장 + 503 {detail}", "enqueue fails → save FAILURE + 503 {detail}")])
down(js, vw, "multipart FormData")
right(ser, vw, "is_valid()")
left(url, ser) if False else None
arrow(f"M{url['cx']} {url['y2']} V{ser['y1'] - 2}", label=T("create() 로", "to create()"), at=(url["cx"], url["y2"] + 17))
right(vw, r202, T("응답", "response"))
y = vw["y2"] + GAP
hc = box("L", y, "out", "GET /api/v1/health/  (django)", T("DB · Redis 연결 확인", "check DB · Redis"), [
    T("config/health.py · 로그인 불필요 · GET 만", "config/health.py · no login · GET only"),
    T("_check_db SELECT 1 · _check_redis ping (2초)", "_check_db SELECT 1 · _check_redis ping (2 s)"),
    T("200 {status, checks} · 하나라도 실패 503", "200 {status, checks} · any failure 503"),
    T("compose django healthcheck 가 부름", "called by compose django healthcheck")])
tk = box("M", y, "py", "tasks.run_analysis(job_id)  · celery", T("큐에서 꺼내 백그라운드 실행", "runs in background"), [
    "config/celery.py autodiscover_tasks → @shared_task",
    T("① get(pk=job_id) → STARTED · started_at 저장", "① get(pk=job_id) → save STARTED · started_at"),
    T("② _prepare_video → ③ predict_video → ④ save_result", "② _prepare_video → ③ predict_video → ④ save_result"),
    T("오류는 어디서든 _fail() · 제한 600초", "any error → _fail() · limit 600 s"),
    T("로그 job#N: 대기 · 영상 · 추론 · 저장 초 (+0900)", "log job#N: wait · video · AI · save s (+0900)")])
rd = box("R", y, "dat", T("Redis (redis:6379/0) · Celery 브로커", "Redis (redis:6379/0) · Celery broker"), T("작업 대기열", "job queue"), [
    T("메시지 = run_analysis · args [job_id] · task_id", "message = run_analysis · args [job_id] · task_id"),
    T("결과 백엔드 /1 = {job_id, status} 만", "result backend /1 = {job_id, status} only"),
    T("업무 데이터는 PostgreSQL · 포트 비공개", "business data in PostgreSQL · port private")], tag="redis")
arrow(f"M{vw['x2']} {vw['y2'] - 14} H{rd['cx']} V{rd['y1'] - 2}", label=T("Redis 메시지 (run_analysis, job_id)", "Redis message (run_analysis, job_id)"), at=(rd["cx"] - 30, vw["y2"] - 24))
left(rd, tk, T("Worker 가 꺼냄", "worker takes"))
y = tk["y2"] + GAP
cap = box("L", y, "py", "camera_capture.capture_clip()", T("휴대폰 카메라 수집", "capture phone camera"), [
    "get_allowed_camera_url(camera_index)",
    T("cv2.VideoCapture · 8초 · 최대 30fps → mp4v", "cv2.VideoCapture · 8 s · max 30 fps → mp4v"),
    T("실제 fps 로 다시 기록 · 실패 → CameraError", "rewrite with real fps · fail → CameraError")])
pv = box("M", y, "py", "tasks._prepare_video(job)", T("분석할 mp4 확보", "get the mp4 to analyze"), [
    T("UPLOAD → media/videos/YYYY/MM/DD/*.mp4", "UPLOAD → media/videos/YYYY/MM/DD/*.mp4"),
    T("WEBCAM → media/captures/YYYY/MM/DD/job_{id}.mp4", "WEBCAM → media/captures/YYYY/MM/DD/job_{id}.mp4"),
    T("  경로를 job.video_file 에 저장", "  path saved to job.video_file")])
vol = box("R", y, "vid", T("media_data 볼륨 (/app/media)", "media_data volume (/app/media)"), T("영상 공유 폴더", "shared video folder"),
          [T("django 가 업로드 저장 ↔ celery 가 읽음", "django saves upload ↔ celery reads it")])
down(tk, pv, T("job 행", "job row")); right(cap, pv, "WEBCAM mp4"); left(vol, pv, "UPLOAD")
y = pv["y2"] + GAP
spv = box("M", y, "py", "services.predict_video(path, job_id)", T("FastAPI 호출", "call FastAPI"), [
    "requests.post(AI_SERVICE_URL + /predict/video)",
    "files={'file': (name, f, 'video/mp4')} · X-Job-ID",
    T("timeout (5, 300) · 400 이상 → AIServiceError", "timeout (5, 300) · ≥ 400 → AIServiceError")])
down(pv, spv, T("mp4 경로 (Path)", "mp4 path (Path)"))
p3_end = spv["y2"] + 24
panel(p2_end + 18, p3_end, T("③ 입력 영상 확보 — backend/ (Django · Celery)", "③ Get the input video — backend/ (Django · Celery)"),
      T("버튼 1번 = AnalysisJob 1행 · 업로드 파일 또는 IP Webcam 8초 수집 영상을 FastAPI 로 보낼 mp4 로 확보",
        "one click = one AnalysisJob row · an uploaded file or an 8 s IP Webcam clip becomes the mp4 sent to FastAPI"))

# ════════════════════════ ④ 추론 ════════════════════════
y = p3_end + 18 + P_HEAD
rt = box("M", y, "py", "routers/predictions.py · predict_video()", T("추론 API 입구", "inference API entry"), [
    T("모델 없음 503 · 확장자 400 · 0MB 400 · 100MB 413", "no model 503 · extension 400 · 0MB 400 · 100MB 413"),
    T("tempfile 에 저장 → run_in_threadpool(process_video)", "save to tempfile → run_in_threadpool(process_video)"),
    T("로그 job#N (X-Job-ID) · frames · tracks · ms", "log job#N (X-Job-ID) · frames · tracks · ms")])
err = box("R", y, "out", T("오류 응답 → AIServiceError", "error response → AIServiceError"), T("실패 사유 전달", "pass the reason"), [
    T("400 확장자 · 빈 파일 · 413 용량 · 503 모델", "400 extension · empty · 413 size · 503 model"),
    T("422 영상 못 읽음 → Celery 가 FAILURE 저장", "422 unreadable → Celery saves FAILURE")])
arrow(f"M{spv['cx']} {spv['y2']} V{rt['y1'] - 2}", label="multipart mp4 · X-Job-ID", at=(spv["cx"], spv["y2"] + 17))
right(rt, err, T("실패 시", "on error"))
y = rt["y2"] + GAP
pr = box("M", y, "py", "PosePipeline.probe_video() → model.track()", T("영상 읽기 · 사람 추적", "read video · track people"), [
    T("probe: fps · frames · width · height · duration_sec", "probe: fps · frames · width · height · duration_sec"),
    "track(stream=True, persist=False, bytetrack.yaml)",
    T("열 수 없음 → VideoReadError → 422", "cannot open → VideoReadError → 422")])
down(rt, pr, T("임시 파일 경로", "temp file path"))
y = pr["y2"] + GAP
kp = box("M", y, "dat", T("Frame 별 관절 · track_id", "joints · track_id per frame"), T("사람별 관절 좌표", "joints per person"), [
    T("boxes.id → track_id · keypoints.xy → (사람, 17, 2)", "boxes.id → track_id · keypoints.xy → (people, 17, 2)"),
    T("영상 시각 t = frame_idx / fps", "video time t = frame_idx / fps")])
down(pr, kp, T("프레임별 결과", "per-frame result"))
y = kp["y2"] + GAP
ff = box("M", y, "py", "multi_person_utils.feature_from_keypoints()", T("관절 → 38개 숫자", "joints → 38 numbers"), [
    "normalize_by_shoulder_width → 17 × 2 = 34",
    T("selected_joint_angles → 4 (팔꿈치 · 무릎)  = 38-D", "selected_joint_angles → 4 (elbow · knee)  = 38-D"),
    T("모양이 (17, 2) 아니거나 NaN → None", "not (17, 2) or NaN → None")])
fu = box("L", y, "cfg", "src/feature_utils.py", T("정규화 · 각도 계산", "normalize · angles"), [
    T("center_keypoints: 골반 중심 = (0, 0)", "center_keypoints: hip center = (0, 0)"),
    T("shoulder_width 로 크기 · calculate_angle", "scale by shoulder_width · calculate_angle")])
down(kp, ff, T("관절 (17, 2)", "joints (17, 2)")); right(fu, ff, T("함수", "functions"))
y = ff["y2"] + GAP
it = box("M", y, "dat", "tracks[track_id].items", T("사람별 시간순 Feature", "time-ordered features per person"), [
    T("[(t, 38-D float32 또는 None), …] · frame_count", "[(t, 38-D float32 or None), …] · frame_count"),
    T("lost_timeout 2초 안에 안 보이면 None 으로 빈칸", "unseen within lost_timeout 2 s → None gap")])
down(ff, it, "38-D float32")
y = it["y2"] + GAP
pt = box("M", y, "py", "action_inference._predict_track()", T("5초 Window → 30 Step", "5 s window → 30 steps"), [
    "TimedFeatureBuffer(5.0) · is_ready(0.8, 0.6, 10)",
    T("0.25초마다 predict_from_window", "predict_from_window every 0.25 s"),
    "→ resample_sequence (30, 38) → flatten (1, 1140)"])
ru = box("L", y, "cfg", "src/realtime_utils.py · sequence_utils.py", T("Window · 보간 도구", "window · resample tools"), [
    "TimedFeatureBuffer · predict_from_window",
    "resample_sequence · flatten_sequence"])
wt = box("R", y, "out", T("5초 Window 가 안 차는 짧은 영상", "short video (window never fills)"), T("짧은 영상 대체 경로", "fallback for short video"), [
    T("mode = whole_track: 유효 10프레임 이상", "mode = whole_track: ≥ 10 valid frames"),
    T("보인 구간 전체를 30 Step 으로 1번 예측", "whole visible span → 30 steps, predict once")])
down(it, pt, T("사람별 시계열", "time series per person")); right(ru, pt, T("함수", "functions")); right(pt, wt, T("짧으면", "if short"))
y = pt["y2"] + GAP
rf = box("M", y, "mdl", "RandomForest.predict_proba()", T("6개 동작 확률 계산", "6 action probabilities"), [
    T("rf_action_baseline.joblib · 입력 (1, 1140) → 확률 (1, 6)", "rf_action_baseline.joblib · (1, 1140) → probs (1, 6)"),
    T("Window 확률 평균 → argmax → action_label · confidence", "mean of windows → argmax → action_label · confidence"),
    T("확률 열 순서 = model.classes_", "column order = model.classes_")], label=True)
down(pt, rf, T("(1, 1140) × Window 수", "(1, 1140) × windows"))
arrow(f"M{st['x1'] + 10} {st['y2']} V{st['y2'] + 22} H10 V{rf['cy']} H{rf['x1'] - 2}", kind="gray",
      label="app.state.action_model", at=(COL["L"] + 90, rf["cy"] - 10))
y = rf["y2"] + GAP
js200 = box("M", y, "out", T("200 JSON (FastAPI 응답)", "200 JSON (FastAPI response)"), T("Celery 에 돌려줄 결과", "result for Celery"), [
    "person_found · message · processing_ms · video{frames…}",
    "model{classes, n_features, sequence_steps, …}",
    "predictions[track_id · action_label · confidence",
    "  · windows · frame_count · mode · probabilities]"], label=True)
down(rf, js200, T("Track 별 Label · 확률", "label · probs per track"))
p4_end = js200["y2"] + 24
panel(p3_end + 18, p4_end, T("④ 추론 — ai_service/ (FastAPI · DB 없음)", "④ Inference — ai_service/ (FastAPI · no DB)"),
      T("mp4 → YOLO Pose · ByteTrack → (사람, 17, 2) → 38-D → 5초 Window · (30, 38) → (1, 1140) → RandomForest → Track 별 action_label",
        "mp4 → YOLO Pose · ByteTrack → (people, 17, 2) → 38-D → 5 s window · (30, 38) → (1, 1140) → RandomForest → action_label per track"))

# ════════════════════════ ⑤ 저장 · 표시 ════════════════════════
y = p4_end + 18 + P_HEAD
sv = box("M", y, "py", "tasks.save_result(job, data)", T("결과를 DB 에 저장", "save result to DB"), [
    T("action_label ∈ models.ActionLabel 6개 확인", "action_label ∈ models.ActionLabel (6)"),
    T("transaction.atomic: 기존 예측 delete → bulk_create", "transaction.atomic: delete old → bulk_create"),
    "job: SUCCESS · video_frames · video_fps · processing_ms",
    T("JSON message → result_message (사람 없음 안내 등)", "JSON message → result_message (e.g. no person)")], label=True)
fl = box("R", y, "out", "tasks._fail(job, message)", T("실패 기록", "record failure"), [
    "CameraError · AIServiceError · SoftTimeLimitExceeded",
    T("FAILURE + error_message + finished_at 저장", "save FAILURE + error_message + finished_at"),
    T("로그 job#N 실패 (총 N초)", "log job#N failed (total N s)")])
arrow(f"M{js200['cx']} {js200['y2']} V{sv['y1'] - 2}", label=T("200 JSON → dict (services.py)", "200 JSON → dict (services.py)"), at=(js200["cx"], js200["y2"] + 17))
arrow(f"M{err['x2']} {err['cy']} H{COL['R'] + BW + 22} V{fl['cy']} H{fl['x2'] + 2}", kind="gray")
y = sv["y2"] + GAP
mdl = box("L", y, "py", "analyses/models.py", T("테이블 · 규칙 정의", "tables · rules"), [
    "AnalysisJob: user · input_type · video_file · status",
    "  celery_task_id · error_message · processing_ms",
    "PersonPrediction: job FK · track_id · action_label",
    "  confidence · window_count · probabilities (JSON)",
    T("visible_to(user) · is_stale · is_uncertain(< 0.55)", "visible_to(user) · is_stale · is_uncertain(< 0.55)")])
db = box("M", y, "out", "PostgreSQL (postgres:5432)", T("영구 저장", "persistent storage"), [
    T("analyses_analysisjob: 작업 1행 · status · 영상 정보", "analyses_analysisjob: 1 row per job · status · video"),
    T("analyses_personprediction: 사람(track) 1명당 1행", "analyses_personprediction: 1 row per person (track)"),
    "UniqueConstraint(job, track_id) · auth_user 1 ─ N job",
    T("볼륨 postgres_data (컨테이너를 지워도 유지)", "volume postgres_data (survives container removal)")], label=True)
down(sv, db, T("ORM bulk_create 행", "ORM bulk_create rows"))
right(mdl, db, T("모델", "model"))
arrow(f"M{fl['cx']} {fl['y2']} V{db['cy']} H{db['x2'] + 2}", label="ORM UPDATE", at=(fl["cx"], db["cy"] - 10))
y = db["y2"] + GAP
srz = box("L", y, "py", T("serializers.py  · 응답 JSON", "serializers.py  · response JSON"), T("DB 행 → JSON", "DB row → JSON"), [
    "AnalysisJobStatusSerializer: status · is_finished",
    "  is_stale · error_message · prediction_count",
    "AnalysisJobSerializer: + video_url · total_seconds",
    "  predictions[] = PersonPredictionSerializer",
    "  action_display · confidence · is_uncertain"])
api = box("M", y, "py", "views.status() · retrieve()  · DRF", T("본인 작업만 조회 응답", "own jobs only"), [
    T("get_queryset: visible_to(user) → 남의 id 404", "get_queryset: visible_to(user) → others' id 404"),
    T("status/ → annotate(Count(predictions)) 만", "status/ → annotate(Count(predictions)) only"),
    T("{id}/ → prefetch predictions · 목록 20개씩", "{id}/ → prefetch predictions · list 20 per page"),
    T("PATCH 제목 · 메모 · DELETE 진행 중 409", "PATCH title · memo · DELETE running 409")])
dash = box("R", y, "py", "page_views.dashboard · dashboard.js", T("관리자 통계", "admin statistics"), [
    "GET /dashboard/ · @staff_member_required",
    T("_count_by() GROUP BY · Avg(processing_ms)", "_count_by() GROUP BY · Avg(processing_ms)"),
    "→ chart_data (json_script) → Chart.js × 4",
    T("/admin/ → admin.py (예측 수 annotate · 필터)", "/admin/ → admin.py (prediction count · filters)")])
down(db, api, T("ORM 조회", "ORM read"))
right(srz, api, T("직렬화", "serialize"))
arrow(f"M{db['x2']} {db['y2'] - 12} H{dash['cx']} V{dash['y1'] - 2}", label=T("ORM 집계 (Count · Avg)", "ORM aggregate (Count · Avg)"), at=(dash["cx"] - 30, db["y2"] - 22))
y = max(api["y2"], srz["y2"], dash["y2"]) + GAP
poll = box("M", y, "py", T("analyses.js · 상태 · 결과 표", "analyses.js · status · result table"), T("결과 표시", "show result"), [
    T("poll(): 2초마다 GET /api/v1/analyses/{id}/status/", "poll(): GET /api/v1/analyses/{id}/status/ every 2 s"),
    T("600초 넘거나 is_stale → 멈추고 안내", "over 600 s or is_stale → stop with notice"),
    T("SUCCESS → showResult(): GET /api/v1/analyses/{id}/", "SUCCESS → showResult(): GET /api/v1/analyses/{id}/"),
    T("is_uncertain → '판단 불확실' 배지", "is_uncertain → 'uncertain' badge")])
det = box("L", y, "py", "page_views.detail · detail.html", T("상세 화면", "detail page"), [
    "GET /analyses/{id}/ · @login_required",
    T("visible_to(user) → 남의 것 404 (API 와 같은 규칙)", "visible_to(user) → others 404 (same as API)"),
    T("새로고침해도 DB 에서 다시 조회", "re-read from DB on refresh")])
down(api, poll, T("상태 JSON · 결과 JSON (2초 · 최대 600초)", "status JSON · result JSON (2 s · max 600 s)"))
arrow(f"M{db['x1'] + 24} {db['y2']} V{mdl['y2'] + 12} H{COL['L'] - 16} V{det['cy']} H{det['x1'] - 2}", label=T("ORM 조회", "ORM read"), at=(COL["L"] + 90, mdl["y2"] + 12))
left(poll, det, T("상세 링크", "detail link"))
p5_end = max(det["y2"], poll["y2"]) + 44
panel(p4_end + 18, p5_end, T("⑤ 저장 · 표시 — Celery 가 Django ORM 으로 저장, 화면은 DB 를 조회", "⑤ Save · display — Celery saves with the Django ORM, screens read the DB"),
      T("FastAPI 는 DB 를 모름 · 결과는 analyses/models.py 의 AnalysisJob 1 ─ N PersonPrediction", "FastAPI never sees the DB · results live in AnalysisJob 1 ─ N PersonPrediction (analyses/models.py)"))

# ════════════════════════ ⑥ 검증 (실행 순서 아님) ════════════════════════
y = p5_end + 18 + P_HEAD
t1 = box("L", y, "test", "analyses/tests.py  · 36", None, [
    T("API: 202 · 400 · 404 · 409 · PATCH 제목만", "API: 202 · 400 · 404 · 409 · PATCH title only"),
    T("/api/v1 주소 · status_url · health 200/503", "/api/v1 URLs · status_url · health 200/503"),
    T("등록 실패 503 · 멈춘 작업 삭제 · 폴링 600초", "enqueue 503 · stuck job delete · poll 600 s"),
    T("job#N 로그 · X-Job-ID · 쿼리 수 · is_uncertain", "job#N logs · X-Job-ID · query count · is_uncertain")])
t2 = box("M", y, "test", "analyses/test_camera_preview.py  · 10", None, [
    T("로그인 필요 · 허용 목록 밖 404", "login required · not allowed 404"),
    T("MJPEG 중계 후 카메라 닫힘 · 60초 끊김", "relays MJPEG then closes · cut at 60 s"),
    T("브라우저 종료 · 카메라 실패 502 (주소 안 보임)", "browser leaves · camera down 502 (no address)")])
t3 = box("R", y, "test", "accounts/tests.py  · 5", None, [
    T("가입 → 바로 로그인 · 로그인 · 로그아웃", "signup → logged in · login · logout"),
    T("미로그인 화면 → 로그인 · API → 401/403", "anonymous page → login · API → 401/403"),
    "GET /api/v1/auth/me/"])
p6_end = max(t1["y2"], t2["y2"], t3["y2"]) + 24
panel(p5_end + 18, p6_end, T("⑥ 검증 — 실행 순서가 아님 · docker compose exec django python manage.py test → 51 OK", "⑥ Verification — not a runtime step · docker compose exec django python manage.py test → 51 OK"),
      T("Celery eager 모드 · predict_video 는 mock 으로 대신 → Redis · FastAPI · 모델 없이 돌아감 · 화살표로 잇지 않음 (코드를 바꾸지 않고 확인만)",
        "Celery eager mode · predict_video mocked → runs without Redis · FastAPI · model · no arrows (checks only, changes nothing)"), dashed=True)

# ════════════════════════ 합치기 ════════════════════════
H = p6_end + 130
add = out.append
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">')
add('<defs>'
    '<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#334155"/></marker>'
    '<marker id="arg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#94A3B8"/></marker>'
    '</defs>')
add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
TITLE = T("Vision Action Platform · 모델 → 추론 → 저장 파이프라인", "Vision Action Platform · model → inference → save pipeline")
SUBT = T("설정 · 모델 파일 → 서버 시작 시 로드 → 버튼 → FormData → mp4 → (사람, 17, 2) → 38-D → (1, 1140) → RandomForest → 200 JSON → DB 행 → 상태 · 결과 JSON → 화면",
         "settings · model files → loaded at start → click → FormData → mp4 → (people, 17, 2) → 38-D → (1, 1140) → RandomForest → 200 JSON → DB rows → status · result JSON → screen")
add(f'<text x="{W / 2}" y="50" font-size="27" font-weight="700" fill="{INK}" text-anchor="middle">{esc(TITLE)}</text>')
add(f'<text x="{W / 2}" y="80" font-size="14" fill="{MUTED}" text-anchor="middle">{esc(SUBT)}</text>')
fit(SUBT, 14, W - 40, "subtitle")
for y1, y2, title, sub, dashed in PANELS:
    dash = ' stroke-dasharray="9 6"' if dashed else ""
    add(f'<rect x="20" y="{y1}" width="{W - 40}" height="{y2 - y1}" rx="12" fill="#F8FAFC" stroke="{"#94A3B8" if dashed else "#E2E8F0"}" stroke-width="{1.8 if dashed else 1.3}"{dash}/>')
    add(f'<text x="40" y="{y1 + 29}" font-size="17" font-weight="700" fill="{INK}">{esc(title)}</text>')
    add(f'<text x="40" y="{y1 + 50}" font-size="12.5" fill="{MUTED}">{esc(sub)}</text>')
    fit(sub, 12.5, W - 80, "panel sub"); fit(title, 17, W - 80, "panel title", True)
draw_arrows()
out.extend(body)

ly = p6_end + 34
add(f'<rect x="40" y="{ly - 10}" width="102" height="20" rx="10" fill="#fff" stroke="{RED}" stroke-width="1.4"/>')
add(f'<circle cx="53" cy="{ly}" r="3.8" fill="{RED}"/><text x="62" y="{ly + 4.5}" font-size="12" font-weight="700" fill="{RED}">action_label</text>')
LBL = T("models/ 의 model.classes_ → predict_proba 열 순서 → JSON action_label → save_result 검사 → PersonPrediction.action_label → 화면 (정답이 아니라 예측값)",
        "model.classes_ in models/ → predict_proba column order → JSON action_label → checked in save_result → PersonPrediction.action_label → screen (a prediction, not ground truth)")
add(f'<text x="156" y="{ly + 5}" font-size="13" fill="{SUB}">{esc(LBL)}</text>')
legend = [("cfg", T("설정 · 직접 작성 파일", "settings · hand-written")), ("vid", T("영상 · 미디어", "video · media")),
          ("py", T("Python · JS 처리", "Python · JS code")), ("dat", T("실행 중 만들어지는 데이터", "runtime data")),
          ("mdl", T("학습 모델 파일", "trained model")), ("out", T("결과 · 저장 · 응답", "result · storage · response")),
          ("test", T("검증 (실행 순서 아님)", "verification (not runtime)"))]
x = 40
for k, t in legend:
    s, f = STYLE[k]
    dash = ' stroke-dasharray="4 3"' if k == "test" else ""
    add(f'<rect x="{x}" y="{ly + 26}" width="30" height="18" rx="3" fill="{f}" stroke="{s}" stroke-width="1.8"{dash}/>')
    add(f'<text x="{x + 38}" y="{ly + 40}" font-size="13" fill="{SUB}">{esc(t)}</text>')
    x += 38 + tw(t, 13) + 30
NOTE = T("화살표 글자 = 오가는 데이터 형식 · 회색 점선 화살표 = 다른 구역에서 넘어오는 객체 · 실패 경로",
         "arrow text = data format passed · gray dashed arrow = object from another section · failure path")
add(f'<text x="40" y="{ly + 72}" font-size="12.5" fill="{MUTED}">{esc(NOTE)}</text>')
add('</svg>')

name = "pipeline.svg" if LANG == "ko" else "pipeline.en.svg"
Path(__file__).with_name(name).write_text("\n".join(out), encoding="utf-8")
print(name, W, H)
for w_ in WARN:
    print("  overflow?", w_)
