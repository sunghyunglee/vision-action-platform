"""DRF API

POST   /api/v1/analyses/               분석 등록 → 202 + 작업 ID·task ID
GET    /api/v1/analyses/               내 분석 목록(관리자는 전체)
GET    /api/v1/analyses/{id}/          상세 + 사람별 결과
PATCH  /api/v1/analyses/{id}/          제목·메모만 수정
DELETE /api/v1/analyses/{id}/          삭제(처리 중이면 409), 사람별 예측·영상 파일도 함께 삭제
GET    /api/v1/analyses/{id}/status/   상태만 가볍게 조회(브라우저 폴링용)
"""
import uuid

from django.db import transaction
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


class AnalysisJobViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]  # PUT(전체 덮어쓰기) 막음
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = AnalysisJob.objects.select_related("user").prefetch_related("predictions")
        user = self.request.user
        if user.is_staff:
            return qs
        # 일반 회원은 본인 작업만. 남의 작업 id로 접근하면 404가 된다.
        return qs.filter(user=user)

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
        transaction.on_commit(lambda: run_analysis.apply_async(args=[job.pk], task_id=task_id))

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
        if job.status in (AnalysisJob.Status.PENDING, AnalysisJob.Status.STARTED):
            return Response({"detail": "분석이 진행 중인 작업은 삭제할 수 없습니다."}, status=status.HTTP_409_CONFLICT)
        if job.video_file:
            job.video_file.delete(save=False)  # Media 파일 정리
        job.delete()  # PersonPrediction은 CASCADE로 함께 삭제
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        return Response(AnalysisJobStatusSerializer(self.get_object()).data)
