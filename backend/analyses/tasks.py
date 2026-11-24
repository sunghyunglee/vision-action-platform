"""Celery Worker가 실행하는 분석 작업.

순서: Job 상태 STARTED → (업로드면 저장된 파일 / IP Webcam이면 카메라 수집)
      → FastAPI /predict/video 호출 → PersonPrediction 저장 + SUCCESS
      실패하면 어디서든 FAILURE + error_message 저장
"""
import logging
import time
from pathlib import Path

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .camera_capture import CameraError, capture_clip
from .models import ActionLabel, AnalysisJob, PersonPrediction
from .services import AIServiceError, predict_video

logger = logging.getLogger(__name__)
VALID_LABELS = set(ActionLabel.values)


def _fail(job, message, t0=None):
    job.status = AnalysisJob.Status.FAILURE
    job.error_message = message[:2000]
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "error_message", "finished_at"])
    took = f" (총 {time.monotonic() - t0:.1f}s)" if t0 is not None else ""
    logger.warning("job#%s 실패%s: %s", job.pk, took, message)


def _prepare_video(job):
    """분석할 영상 파일 경로를 확보한다."""
    if job.input_type == AnalysisJob.InputType.UPLOAD:
        if not job.video_file:
            raise CameraError("업로드된 영상 파일이 없습니다.")
        return Path(job.video_file.path)

    # IP Webcam: 정해진 시간만 수집해 Media에 저장하고 Job에 경로를 기록
    rel = Path("captures") / timezone.localtime().strftime("%Y/%m/%d") / f"job_{job.pk}.mp4"
    abs_path = Path(settings.MEDIA_ROOT) / rel
    capture_clip(job.camera_index, job.capture_seconds or settings.CAMERA_CAPTURE_SECONDS, abs_path)
    job.video_file.name = str(rel)
    job.save(update_fields=["video_file"])
    return abs_path


def save_result(job, data):
    """FastAPI 응답을 Django ORM으로 저장. 6개 Action 밖의 Label이 오면 실패로 처리."""
    preds = data.get("predictions") or []
    for p in preds:
        if p.get("action_label") not in VALID_LABELS:
            raise AIServiceError(f"모델이 알 수 없는 Label을 반환했습니다: {p.get('action_label')}")

    video = data.get("video") or {}
    with transaction.atomic():
        job.predictions.all().delete()  # 재시도 시 중복 방지
        PersonPrediction.objects.bulk_create([
            PersonPrediction(
                job=job,
                track_id=int(p["track_id"]),
                action_label=p["action_label"],
                confidence=float(p["confidence"]),
                # PM 계약은 windows, 초기 구현은 window_count → 둘 다 허용
                window_count=int(p.get("windows", p.get("window_count", 0)) or 0),
                frame_count=int(p.get("frame_count", 0)),
                probabilities=p.get("probabilities") or {},
            )
            for p in preds
        ])
        job.status = AnalysisJob.Status.SUCCESS
        job.error_message = ""
        msg = data.get("message") or ""
        if data.get("person_found") is False and not msg:
            msg = "영상에서 사람을 찾지 못했습니다."
        job.result_message = msg[:255]
        job.video_frames = video.get("frames")
        job.video_fps = video.get("fps")
        job.video_duration_sec = video.get("duration_sec")
        job.processing_ms = data.get("processing_ms", data.get("processing_time_ms"))
        job.finished_at = timezone.now()
        job.save()


@shared_task(bind=True)
def run_analysis(self, job_id):
    try:
        job = AnalysisJob.objects.get(pk=job_id)
    except AnalysisJob.DoesNotExist:
        logger.error("job#%s 가 DB에 없습니다(삭제되었거나 커밋 전).", job_id)
        return {"job_id": job_id, "status": "MISSING"}

    job.status = AnalysisJob.Status.STARTED
    job.started_at = timezone.now()
    if self.request.id and not job.celery_task_id:
        job.celery_task_id = self.request.id
    job.save(update_fields=["status", "started_at", "celery_task_id"])

    # 작업 1건을 로그로 끝까지 따라갈 수 있게: job id · 단계 · 걸린 시간을 남긴다
    t0 = time.monotonic()
    wait_s = (job.started_at - job.created_at).total_seconds()
    logger.info("job#%s 시작 input=%s task=%s 대기열 대기 %.1fs", job_id, job.input_type, job.celery_task_id, wait_s)
    try:
        video_path = _prepare_video(job)
        t1 = time.monotonic()
        logger.info("job#%s 영상 확보 %.1fs (%s)", job_id, t1 - t0, video_path.name)

        data = predict_video(video_path, job_id=job_id)
        t2 = time.monotonic()
        logger.info("job#%s AI 추론 응답 %.1fs predictions=%d processing_ms=%s",
                    job_id, t2 - t1, len(data.get("predictions") or []), data.get("processing_ms"))

        save_result(job, data)
        logger.info("job#%s 저장 완료 %s 총 %.1fs", job_id, job.status, time.monotonic() - t0)
    except (CameraError, AIServiceError) as e:
        _fail(job, str(e), t0)
    except SoftTimeLimitExceeded:
        _fail(job, f"작업 제한 시간({settings.CELERY_TASK_SOFT_TIME_LIMIT}초)을 넘었습니다.", t0)
    except Exception as e:  # 예상하지 못한 오류도 FAILURE로 남긴다
        logger.exception("job#%s 처리 중 예외", job_id)
        _fail(job, f"알 수 없는 오류: {type(e).__name__}: {e}", t0)

    return {"job_id": job_id, "status": job.status}
