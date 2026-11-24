"""POST /predict/video : Celery Worker가 보낸 영상 1건을 분석해 사람별 예측을 반환한다.

응답 규칙(API 계약)
- 200 + person_found true  : predictions에 사람별 결과(track_id, action_label, confidence, windows)
- 200 + person_found false : 영상은 정상, 사람 미검출 → predictions = [] + message
  (사람은 보였지만 30 Step을 못 채우면 person_found true + predictions [] + message)
- 400 : 확장자·빈 파일
- 422 : 영상을 열 수 없음(손상·코덱) → Celery가 FAILURE로 저장
- 413 : 파일이 너무 큼
- 503 : 모델이 아직 준비되지 않음
"""
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from services.action_inference import predict_tracks
from services.pose_pipeline import VideoReadError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["predictions"])

ALLOWED_EXT = {".mp4", ".mov", ".avi", ".mkv"}
MAX_MB = int(os.environ.get("MAX_UPLOAD_MB", "100"))


@router.post("/predict/video")
async def predict_video(request: Request, file: UploadFile = File(...)):
    state = request.app.state
    if state.action_model is None or state.pose is None:
        raise HTTPException(503, f"모델이 준비되지 않았습니다: {state.load_error}")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"지원하지 않는 영상 형식입니다({ext or '확장자 없음'}).")

    # 업로드를 임시 파일로 저장(OpenCV는 파일 경로로 읽음)
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    try:
        with tmp:
            shutil.copyfileobj(file.file, tmp)
        size_mb = os.path.getsize(tmp.name) / 1024 / 1024
        if size_mb == 0:
            raise HTTPException(400, "빈 파일입니다.")
        if size_mb > MAX_MB:
            raise HTTPException(413, f"파일이 너무 큽니다({size_mb:.1f}MB > {MAX_MB}MB).")

        t0 = time.perf_counter()
        try:
            # YOLO 추론은 CPU를 오래 쓰므로 이벤트 루프를 막지 않게 스레드에서 실행
            pose_result = await run_in_threadpool(state.pose.process_video, tmp.name)
        except VideoReadError as e:
            raise HTTPException(422, str(e))
        predictions = await run_in_threadpool(predict_tracks, state.action_model, pose_result["tracks"], state.config)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
    finally:
        os.unlink(tmp.name)

    person_found = bool(pose_result["tracks"])
    if predictions:
        message = f"{len(predictions)}명의 동작을 예측했습니다."
    elif person_found:
        message = "사람은 검출됐지만 동작을 판단할 만큼 관절이 충분히 보이지 않았습니다(유효 프레임 10개 미만)."
    else:
        message = "영상에서 사람을 찾지 못했습니다."

    job_id = request.headers.get("x-job-id", "-")  # Celery가 보낸 작업 번호(없으면 단독 호출)
    logger.info("job#%s %s: %d frames, %d tracks, %d predictions, %d ms", job_id,
                file.filename, pose_result["video"]["frames"], len(pose_result["tracks"]), len(predictions), elapsed_ms)
    return {
        "person_found": person_found,
        "message": message,
        "processing_ms": elapsed_ms,
        "video": pose_result["video"],
        "model": {"classes": state.action_model.classes, "n_features": state.action_model.n_features,
                  "sequence_steps": state.action_model.sequence_steps,
                  "window_seconds": state.config["day07_realtime"]["window_seconds"],
                  "confidence_threshold": state.config["day07_realtime"]["confidence_threshold"]},
        "predictions": predictions,
    }
