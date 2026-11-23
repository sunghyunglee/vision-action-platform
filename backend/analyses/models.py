"""
업무 테이블 2개.

auth_user(Django 기본) 1 ── N AnalysisJob 1 ── N PersonPrediction

- AnalysisJob     : 분석 요청 1건(누가, 어떤 입력으로, 지금 어떤 상태인지)
- PersonPrediction: 그 작업 영상 속 사람(track_id) 1명당 예측 1행
"""
from django.conf import settings
from django.db import models


class ActionLabel(models.TextChoices):
    """6일차 모델이 아는 6개 동작. 이 밖의 Label은 저장하지 않는다."""

    BEND_RETURN = "bend_return", "A001 허리 굽혔다 펴기"
    LEG_RAISE_LOWER = "leg_raise_lower", "A002 다리 들었다 내리기"
    WALK_TURN_WALK = "walk_turn_walk", "A003 걷다가 돌아 걷기"
    DRINK_RETURN = "drink_return", "A004 마시고 돌아오기"
    SIT_STAND = "sit_stand", "A005 앉았다 일어나기"
    WAVE = "wave", "A006 손 흔들기"


class AnalysisJob(models.Model):
    class InputType(models.TextChoices):
        UPLOAD = "UPLOAD", "영상 업로드"
        WEBCAM = "WEBCAM", "IP Webcam"

    class Status(models.TextChoices):
        # Celery 상태 표기와 같은 대문자로 통일
        PENDING = "PENDING", "대기"
        STARTED = "STARTED", "처리 중"
        SUCCESS = "SUCCESS", "완료"
        FAILURE = "FAILURE", "실패"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="analysis_jobs", verbose_name="요청 사용자"
    )
    title = models.CharField("제목", max_length=100, blank=True)
    memo = models.TextField("메모", blank=True)

    input_type = models.CharField("입력 방식", max_length=20, choices=InputType.choices)
    # 영상 파일 자체는 Media 저장소에 두고 DB에는 경로만 기록한다.
    video_file = models.FileField("영상 파일", upload_to="videos/%Y/%m/%d/", blank=True)
    # 카메라 URL은 저장하지 않고 허용 목록(IP_WEBCAM_ALLOWED_URLS)의 번호만 저장한다.
    camera_index = models.PositiveSmallIntegerField("카메라 번호", null=True, blank=True)
    capture_seconds = models.PositiveSmallIntegerField("수집 시간(초)", null=True, blank=True)

    # 사용자가 '하려던 동작'. 검증된 정답 Label이 아니다.
    expected_action = models.CharField(
        "수행하려던 동작(사용자 입력)", max_length=30, choices=ActionLabel.choices, blank=True
    )

    status = models.CharField("상태", max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    celery_task_id = models.CharField("Celery task ID", max_length=64, blank=True, db_index=True)
    error_message = models.TextField("에러 메시지", blank=True)
    result_message = models.CharField("결과 메시지", max_length=255, blank=True)  # 예: 사람을 찾지 못했습니다

    # FastAPI가 알려 준 영상·처리 정보
    video_frames = models.PositiveIntegerField("프레임 수", null=True, blank=True)
    video_fps = models.FloatField("FPS", null=True, blank=True)
    video_duration_sec = models.FloatField("영상 길이(초)", null=True, blank=True)
    processing_ms = models.PositiveIntegerField("AI 추론 시간(ms)", null=True, blank=True)

    created_at = models.DateTimeField("생성 시간", auto_now_add=True)
    started_at = models.DateTimeField("시작 시간", null=True, blank=True)
    finished_at = models.DateTimeField("완료 시간", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "분석 작업"
        verbose_name_plural = "분석 작업"

    def __str__(self):
        return f"#{self.pk} {self.get_input_type_display()} {self.status}"

    @property
    def is_finished(self):
        return self.status in (self.Status.SUCCESS, self.Status.FAILURE)

    @property
    def total_seconds(self):
        """요청 생성부터 완료까지 걸린 전체 시간(대기·수집·추론 포함)."""
        if self.finished_at:
            return round((self.finished_at - self.created_at).total_seconds(), 1)
        return None


class PersonPrediction(models.Model):
    job = models.ForeignKey(AnalysisJob, on_delete=models.CASCADE, related_name="predictions", verbose_name="분석 작업")
    # 한 작업(영상) 안에서만 의미 있는 추적 번호. 영구적인 사람 ID가 아니다.
    track_id = models.IntegerField("Track ID")
    action_label = models.CharField("예측 동작", max_length=30, choices=ActionLabel.choices)
    confidence = models.FloatField("Confidence")
    window_count = models.PositiveIntegerField("처리한 Window 수", default=0)
    frame_count = models.PositiveIntegerField("검출된 프레임 수", default=0)
    probabilities = models.JSONField("Class별 확률", default=dict, blank=True)
    created_at = models.DateTimeField("예측 시간", auto_now_add=True)

    class Meta:
        ordering = ["job_id", "track_id"]
        constraints = [models.UniqueConstraint(fields=["job", "track_id"], name="uniq_track_per_job")]
        verbose_name = "사람별 예측"
        verbose_name_plural = "사람별 예측"

    def __str__(self):
        return f"job#{self.job_id} track{self.track_id} {self.action_label} {self.confidence:.2f}"

    @property
    def is_uncertain(self):
        return self.confidence < settings.LOW_CONFIDENCE_THRESHOLD
