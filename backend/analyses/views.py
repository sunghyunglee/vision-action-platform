"""DRF API

POST   /api/v1/analyses/               분석 등록 → 202 + 작업 ID·task ID
GET    /api/v1/analyses/               내 분석 목록(관리자는 전체)
GET    /api/v1/analyses/{id}/          상세 + 사람별 결과
PATCH  /api/v1/analyses/{id}/          제목·메모만 수정
DELETE /api/v1/analyses/{id}/          삭제(처리 중이면 409, 단 멈춘 작업은 허용), 사람별 예측·영상 파일도 함께 삭제
GET    /api/v1/analyses/{id}/status/   상태만 가볍게 조회(브라우저 폴링용)
"""
import logging
import uuid

from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.urls import reverse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import AnalysisJob
from .serializers import (
    AnalysisJobCreateSerializer,
    AnalysisJobSerializer,
    AnalysisJobStatusSerializer,
    AnalysisJobUpdateSerializer,
)
from .tasks import run_analysis

logger = logging.getLogger(__name__)

ENQUEUE_FAILED_MESSAGE = "작업 대기열(Redis)에 등록하지 못했습니다. Redis와 Celery Worker 상태를 확인한 뒤 다시 시도하세요."


def enqueue_analysis(job_pk, task_id):
    """Celery 작업을 Redis에 등록. 실패하면 PENDING으로 남기지 않고 바로 FAILURE로 저장한다."""
    try:
        run_analysis.apply_async(args=[job_pk], task_id=task_id)
        logger.info("job#%s 대기열 등록 task=%s", job_pk, task_id)
    except Exception as e:  # Redis 연결 거부·타임아웃 등
        logger.error("job#%s 대기열 등록 실패: %s: %s", job_pk, type(e).__name__, e)
        AnalysisJob.objects.filter(pk=job_pk, status=AnalysisJob.Status.PENDING).update(
            status=AnalysisJob.Status.FAILURE,
            error_message=ENQUEUE_FAILED_MESSAGE,
            finished_at=timezone.now(),
        )


class AnalysisJobViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]  # PUT(전체 덮어쓰기) 막음
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        # 일반 회원은 본인 작업만, 관리자는 전체 (남의 작업 id로 접근하면 404)
        qs = AnalysisJob.objects.visible_to(self.request.user)
        if self.action == "status":
            # 화면이 2초마다 부르는 폴링: 예측 행(확률 JSON 포함)은 읽지 않고 개수만 COUNT로 함께 가져온다
            return qs.annotate(prediction_count=Count("predictions"))
        return qs.select_related("user").prefetch_related("predictions")

    def get_serializer_class(self):
        if self.action == "create":
            return AnalysisJobCreateSerializer
        if self.action == "partial_update":
            return AnalysisJobUpdateSerializer
        if self.action == "status":
            return AnalysisJobStatusSerializer
        return AnalysisJobSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task_id = str(uuid.uuid4())  # task ID를 미리 정해 DB에 함께 저장
        job = serializer.save(user=request.user, celery_task_id=task_id)

        # DB 커밋이 끝난 뒤에 Redis에 등록 → Worker가 아직 없는 행을 읽는 일을 막는다
        transaction.on_commit(lambda: enqueue_analysis(job.pk, task_id))

        # 요청이 트랜잭션 밖이면 on_commit은 바로 실행된다 → 등록 실패를 즉시 알려 준다
        job.refresh_from_db(fields=["status", "error_message"])
        if job.status == AnalysisJob.Status.FAILURE:
            return Response(
                {"id": job.pk, "task_id": task_id, "status": job.status, "detail": job.error_message},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "id": job.pk,
                "task_id": task_id,
                "status": job.status,
                "status_url": reverse("api:analysis-status", args=[job.pk]),
            },
            status=status.HTTP_202_ACCEPTED,
        )

    def partial_update(self, request, *args, **kwargs):
        job = self.get_object()
        serializer = AnalysisJobUpdateSerializer(job, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AnalysisJobSerializer(job, context={"request": request}).data)

    def destroy(self, request, *args, **kwargs):
        job = self.get_object()
        running = job.status in (AnalysisJob.Status.PENDING, AnalysisJob.Status.STARTED)
        if running and not job.is_stale:
            return Response({"detail": "분석이 진행 중인 작업은 삭제할 수 없습니다."}, status=status.HTTP_409_CONFLICT)
        if running:
            logger.info("job#%s 멈춘 작업(%s) 삭제", job.pk, job.status)
        if job.video_file:
            job.video_file.delete(save=False)  # Media 파일 정리
        job.delete()  # PersonPrediction은 CASCADE로 함께 삭제
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        return Response(AnalysisJobStatusSerializer(self.get_object()).data)
