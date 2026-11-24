"""HTML 화면. 데이터 변경은 DRF API(views.py)가 맡고, 여기서는 화면만 그린다."""
import json

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, render

from .models import ActionLabel, AnalysisJob, PersonPrediction


@login_required
def index(request):
    recent = AnalysisJob.objects.filter(user=request.user).prefetch_related("predictions")[:10]
    cameras = [{"index": i, "label": f"카메라 {i + 1}"} for i in range(len(settings.IP_WEBCAM_ALLOWED_URLS))]
    return render(request, "analyses/index.html", {
        "recent_jobs": recent,
        "cameras": cameras,
        "actions": ActionLabel.choices,
        "capture_seconds": settings.CAMERA_CAPTURE_SECONDS,
        "preview_seconds": settings.CAMERA_PREVIEW_MAX_SECONDS,
        "allowed_ext": ",".join("." + e for e in settings.ALLOWED_VIDEO_EXTENSIONS),
        "max_upload_mb": settings.MAX_UPLOAD_MB,
        "poll_timeout_seconds": settings.POLL_TIMEOUT_SECONDS,
    })


@login_required
def detail(request, pk):
    job = get_object_or_404(AnalysisJob.objects.visible_to(request.user).prefetch_related("predictions"), pk=pk)
    return render(request, "analyses/detail.html", {"job": job, "low_conf": settings.LOW_CONFIDENCE_THRESHOLD})


@staff_member_required
def dashboard(request):
    """관리자 전용. Django ORM 집계 결과를 Chart.js에 넘긴다(FastAPI는 DB를 모른다)."""
    action_counts = dict(
        PersonPrediction.objects.values_list("action_label").annotate(n=Count("id")).values_list("action_label", "n")
    )
    status_counts = dict(AnalysisJob.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    input_counts = dict(
        AnalysisJob.objects.values_list("input_type").annotate(n=Count("id")).values_list("input_type", "n")
    )
    avg_ms = (
        AnalysisJob.objects.filter(status=AnalysisJob.Status.SUCCESS)
        .values("input_type").annotate(avg=Avg("processing_ms"))
    )

    chart_data = {
        "actions": {
            "labels": [v for v, _ in ActionLabel.choices],
            "counts": [action_counts.get(v, 0) for v, _ in ActionLabel.choices],
        },
        "statuses": {
            "labels": [v for v, _ in AnalysisJob.Status.choices],
            "counts": [status_counts.get(v, 0) for v, _ in AnalysisJob.Status.choices],
        },
        "inputs": {
            "labels": [str(lbl) for _, lbl in AnalysisJob.InputType.choices],
            "counts": [input_counts.get(v, 0) for v, _ in AnalysisJob.InputType.choices],
        },
        "avg_ms": {row["input_type"]: round(row["avg"] or 0) for row in avg_ms},
    }
    return render(request, "analyses/dashboard.html", {
        "chart_data": chart_data,
        "total_jobs": sum(status_counts.values()),
        "total_predictions": sum(action_counts.values()),
        "recent_jobs": AnalysisJob.objects.select_related("user")[:15],
    })
