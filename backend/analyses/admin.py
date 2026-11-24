from django.contrib import admin
from django.db.models import Count

from .models import AnalysisJob, PersonPrediction


class PersonPredictionInline(admin.TabularInline):
    model = PersonPrediction
    extra = 0
    fields = ("track_id", "action_label", "confidence", "window_count", "frame_count", "created_at")
    readonly_fields = fields
    can_delete = False


@admin.register(AnalysisJob)
class AnalysisJobAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "input_type", "status", "expected_action",
                    "prediction_count", "processing_ms", "created_at", "finished_at")
    list_filter = ("status", "input_type", "expected_action", "created_at")
    search_fields = ("user__username", "title", "memo", "celery_task_id")
    readonly_fields = ("celery_task_id", "status", "error_message", "result_message", "video_frames", "video_fps",
                       "video_duration_sec", "processing_ms", "created_at", "started_at", "finished_at")
    date_hierarchy = "created_at"
    inlines = [PersonPredictionInline]

    def get_queryset(self, request):
        # 목록의 '예측 수'를 행마다 COUNT 하지 않고(N+1) 한 번의 쿼리로 함께 집계
        return super().get_queryset(request).annotate(_prediction_count=Count("predictions"))

    @admin.display(description="예측 수")
    def prediction_count(self, obj):
        return obj._prediction_count


@admin.register(PersonPrediction)
class PersonPredictionAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "job_user", "track_id", "action_label", "confidence", "window_count", "created_at")
    list_filter = ("action_label", "job__input_type", "job__status")
    search_fields = ("job__user__username", "job__id")
    list_select_related = ("job", "job__user")

    @admin.display(description="요청 사용자", ordering="job__user__username")
    def job_user(self, obj):
        return obj.job.user
