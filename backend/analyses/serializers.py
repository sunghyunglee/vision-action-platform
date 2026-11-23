from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from .models import AnalysisJob, PersonPrediction


class PersonPredictionSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_label_display", read_only=True)
    is_uncertain = serializers.BooleanField(read_only=True)

    class Meta:
        model = PersonPrediction
        fields = (
            "id", "track_id", "action_label", "action_display", "confidence", "is_uncertain",
            "window_count", "frame_count", "probabilities", "created_at",
        )
        read_only_fields = fields


class AnalysisJobSerializer(serializers.ModelSerializer):
    """조회(목록·상세) 응답. 모든 값을 읽기 전용으로 보여 준다."""

    username = serializers.CharField(source="user.username", read_only=True)
    input_type_display = serializers.CharField(source="get_input_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    video_url = serializers.SerializerMethodField()
    total_seconds = serializers.FloatField(read_only=True)
    predictions = PersonPredictionSerializer(many=True, read_only=True)

    class Meta:
        model = AnalysisJob
        fields = (
            "id", "username", "title", "memo", "input_type", "input_type_display",
            "video_url", "camera_index", "capture_seconds", "expected_action",
            "status", "status_display", "celery_task_id", "error_message", "result_message",
            "video_frames", "video_fps", "video_duration_sec", "processing_ms", "total_seconds",
            "created_at", "started_at", "finished_at", "predictions",
        )
        read_only_fields = fields

    def get_video_url(self, obj):
        return obj.video_file.url if obj.video_file else None


class AnalysisJobCreateSerializer(serializers.ModelSerializer):
    """POST /api/analyses/ 입력 검사. 상태·결과 필드는 받지 않는다."""

    video_file = serializers.FileField(required=False, allow_empty_file=False)
    camera_index = serializers.IntegerField(required=False, min_value=0)

    class Meta:
        model = AnalysisJob
        fields = ("title", "memo", "input_type", "video_file", "camera_index", "expected_action")

    def validate_video_file(self, f):
        ext = Path(f.name).suffix.lower().lstrip(".")
        if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
            raise serializers.ValidationError(
                f"지원하지 않는 형식입니다(.{ext}). 허용: {', '.join(settings.ALLOWED_VIDEO_EXTENSIONS)}"
            )
        if f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise serializers.ValidationError(f"파일이 너무 큽니다. 최대 {settings.MAX_UPLOAD_MB}MB")
        return f

    def validate(self, attrs):
        input_type = attrs.get("input_type")
        if input_type == AnalysisJob.InputType.UPLOAD:
            if not attrs.get("video_file"):
                raise serializers.ValidationError({"video_file": "분석할 영상 파일을 선택하세요."})
            attrs.pop("camera_index", None)
        elif input_type == AnalysisJob.InputType.WEBCAM:
            cameras = settings.IP_WEBCAM_ALLOWED_URLS
            if not cameras:
                raise serializers.ValidationError({"camera_index": "서버에 허용된 IP Webcam이 등록되어 있지 않습니다."})
            idx = attrs.get("camera_index", 0)
            if idx >= len(cameras):
                raise serializers.ValidationError({"camera_index": "허용 목록에 없는 카메라입니다."})
            attrs["camera_index"] = idx
            attrs["capture_seconds"] = settings.CAMERA_CAPTURE_SECONDS
            attrs.pop("video_file", None)
        return attrs


class AnalysisJobUpdateSerializer(serializers.ModelSerializer):
    """PATCH: 제목·메모만 수정할 수 있다. 상태와 AI 결과는 사용자가 바꿀 수 없다."""

    class Meta:
        model = AnalysisJob
        fields = ("title", "memo")


class AnalysisJobStatusSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_finished = serializers.BooleanField(read_only=True)
    prediction_count = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisJob
        fields = (
            "id", "status", "status_display", "is_finished", "error_message", "result_message",
            "celery_task_id", "prediction_count", "started_at", "finished_at",
        )
        read_only_fields = fields

    def get_prediction_count(self, obj):
        return obj.predictions.count()
