"""과제 기능 테스트(T05~T09 중 웹 서버에서 확인 가능한 부분).

FastAPI·Redis 없이 돌도록 Celery는 eager 모드, AI 호출은 mock으로 대체한다.
실행: python manage.py test
"""
import shutil
import tempfile
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from config.celery import app as celery_app

from .models import AnalysisJob, PersonPrediction
from .services import AIServiceError

TMP_MEDIA = tempfile.mkdtemp()

FAKE_RESPONSE = {
    "status": "ok",
    "message": "2명의 동작을 예측했습니다.",
    "processing_ms": 1234,
    "person_found": True,
    "video": {"frames": 120, "fps": 30.0, "duration_sec": 4.0},
    "predictions": [
        {"track_id": 1, "action_label": "wave", "confidence": 0.82, "windows": 5, "frame_count": 110,
         "probabilities": {"wave": 0.82}},
        {"track_id": 2, "action_label": "sit_stand", "confidence": 0.41, "window_count": 3, "frame_count": 80,
         "probabilities": {"sit_stand": 0.41}},
    ],
}


def mp4(name="clip.mp4"):
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42" + b"0" * 100, content_type="video/mp4")


@override_settings(MEDIA_ROOT=TMP_MEDIA, IP_WEBCAM_ALLOWED_URLS=["http://192.168.0.10:8080/video"])
class AnalysisApiTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        celery_app.conf.task_always_eager = True

    @classmethod
    def tearDownClass(cls):
        celery_app.conf.task_always_eager = False
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.a = User.objects.create_user("user_a", password="Str0ng-pass-123")
        self.b = User.objects.create_user("user_b", password="Str0ng-pass-123")
        self.admin = User.objects.create_user("boss", password="Str0ng-pass-123", is_staff=True)

    def login(self, user):
        self.client.force_login(user)

    def create_upload(self, **extra):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post("/api/v1/analyses/", {"input_type": "UPLOAD", "video_file": mp4(), **extra})

    # T05 비동기: 202 + 작업 ID·task ID 즉시 반환
    @mock.patch("analyses.tasks.predict_video", return_value=FAKE_RESPONSE)
    def test_create_returns_job_id_and_saves_predictions(self, m):
        self.login(self.a)
        res = self.create_upload(title="손 흔들기", expected_action="wave")
        self.assertEqual(res.status_code, 202)
        body = res.json()
        self.assertIn("task_id", body)
        job = AnalysisJob.objects.get(pk=body["id"])
        # T04·T06: 한 작업에 Track ID별 결과 2건이 DB에 저장됨
        self.assertEqual(job.status, "SUCCESS")
        self.assertEqual(job.celery_task_id, body["task_id"])
        self.assertEqual(job.predictions.count(), 2)
        self.assertEqual(job.processing_ms, 1234)
        status = self.client.get(f"/api/v1/analyses/{job.pk}/status/").json()
        self.assertTrue(status["is_finished"])
        self.assertEqual(status["prediction_count"], 2)
        detail = self.client.get(f"/api/v1/analyses/{job.pk}/").json()
        self.assertTrue(detail["predictions"][1]["is_uncertain"])  # 0.41 < 0.5

    def test_create_requires_file_for_upload(self):
        self.login(self.a)
        res = self.client.post("/api/v1/analyses/", {"input_type": "UPLOAD"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("video_file", res.json())

    def test_rejects_wrong_extension(self):
        self.login(self.a)
        bad = SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")
        res = self.client.post("/api/v1/analyses/", {"input_type": "UPLOAD", "video_file": bad})
        self.assertEqual(res.status_code, 400)

    def test_rejects_camera_not_in_allow_list(self):
        self.login(self.a)
        res = self.client.post("/api/v1/analyses/", {"input_type": "WEBCAM", "camera_index": 5})
        self.assertEqual(res.status_code, 400)

    # T09 예외: AI 서버 오류 → FAILURE + 사유 저장
    @mock.patch("analyses.tasks.predict_video", side_effect=AIServiceError("AI 서버(FastAPI)에 연결할 수 없습니다."))
    def test_ai_failure_saved(self, m):
        self.login(self.a)
        job_id = self.create_upload().json()["id"]
        job = AnalysisJob.objects.get(pk=job_id)
        self.assertEqual(job.status, "FAILURE")
        self.assertIn("연결할 수 없습니다", job.error_message)

    # T09 예외: 카메라 연결 실패 → FAILURE
    @mock.patch("analyses.camera_capture.cv2.VideoCapture")
    def test_camera_failure_saved(self, cap):
        cap.return_value.isOpened.return_value = False
        self.login(self.a)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post("/api/v1/analyses/", {"input_type": "WEBCAM", "camera_index": 0})
        job = AnalysisJob.objects.get(pk=res.json()["id"])
        self.assertEqual(job.status, "FAILURE")
        self.assertIn("카메라", job.error_message)

    @mock.patch("analyses.tasks.predict_video", return_value={**FAKE_RESPONSE, "predictions": [
        {"track_id": 1, "action_label": "jump", "confidence": 0.9}]})
    def test_unknown_label_is_failure(self, m):
        self.login(self.a)
        job = AnalysisJob.objects.get(pk=self.create_upload().json()["id"])
        self.assertEqual(job.status, "FAILURE")
        self.assertEqual(PersonPrediction.objects.count(), 0)

    # T07 권한: B는 A의 작업을 조회·수정·삭제할 수 없음
    @mock.patch("analyses.tasks.predict_video", return_value=FAKE_RESPONSE)
    def test_other_user_cannot_access(self, m):
        self.login(self.a)
        job_id = self.create_upload().json()["id"]
        self.login(self.b)
        self.assertEqual(self.client.get(f"/api/v1/analyses/{job_id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/analyses/{job_id}/status/").status_code, 404)
        self.assertEqual(self.client.patch(f"/api/v1/analyses/{job_id}/", {"memo": "x"},
                                           content_type="application/json").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/analyses/{job_id}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/analyses/").json()["count"], 0)
        self.assertEqual(self.client.get(f"/analyses/{job_id}/").status_code, 404)

    # Update: 제목·메모만 바뀌고 상태·결과는 그대로
    @mock.patch("analyses.tasks.predict_video", return_value=FAKE_RESPONSE)
    def test_patch_only_title_memo(self, m):
        self.login(self.a)
        job_id = self.create_upload().json()["id"]
        res = self.client.patch(f"/api/v1/analyses/{job_id}/",
                                {"title": "새 제목", "status": "FAILURE", "memo": "메모"},
                                content_type="application/json")
        self.assertEqual(res.status_code, 200)
        job = AnalysisJob.objects.get(pk=job_id)
        self.assertEqual((job.title, job.memo, job.status), ("새 제목", "메모", "SUCCESS"))
        self.assertEqual(self.client.put(f"/api/v1/analyses/{job_id}/", {}).status_code, 405)

    # Delete: 예측도 함께 삭제, 진행 중이면 409
    @mock.patch("analyses.tasks.predict_video", return_value=FAKE_RESPONSE)
    def test_delete_policy(self, m):
        self.login(self.a)
        job_id = self.create_upload().json()["id"]
        self.assertEqual(self.client.delete(f"/api/v1/analyses/{job_id}/").status_code, 204)
        self.assertEqual(PersonPrediction.objects.count(), 0)
        running = AnalysisJob.objects.create(user=self.a, input_type="UPLOAD", status="STARTED")
        self.assertEqual(self.client.delete(f"/api/v1/analyses/{running.pk}/").status_code, 409)

    # T08 관리자: 전체 목록 + 대시보드, 일반 회원은 대시보드 차단
    @mock.patch("analyses.tasks.predict_video", return_value=FAKE_RESPONSE)
    def test_admin_sees_all_and_dashboard(self, m):
        self.login(self.a)
        self.create_upload()
        self.assertEqual(self.client.get("/dashboard/").status_code, 302)
        self.login(self.admin)
        self.assertEqual(self.client.get("/api/v1/analyses/").json()["count"], 1)
        res = self.client.get("/dashboard/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["chart_data"]["actions"]["counts"][5], 1)  # wave
        self.assertEqual(res.context["chart_data"]["statuses"]["counts"][2], 1)  # SUCCESS

    def test_index_page_renders(self):
        self.login(self.a)
        res = self.client.get("/")
        self.assertContains(res, "AI 분석 시작")
        self.assertContains(res, "IP Webcam")
        self.assertNotContains(res, "192.168.0.10")  # 카메라 주소는 화면에 노출하지 않음


class UrlStructureTests(TestCase):
    """API는 /api/v1/ 한 곳, 화면 주소는 그대로. 주소는 reverse()로 만든다."""

    def test_api_urls_are_versioned(self):
        from django.urls import reverse
        self.assertEqual(reverse("api:analysis-list"), "/api/v1/analyses/")
        self.assertEqual(reverse("api:analysis-detail", args=[3]), "/api/v1/analyses/3/")
        self.assertEqual(reverse("api:analysis-status", args=[3]), "/api/v1/analyses/3/status/")
        self.assertEqual(reverse("api:me"), "/api/v1/auth/me/")
        self.assertEqual(reverse("analyses:detail", args=[3]), "/analyses/3/")

    def test_old_api_urls_removed(self):
        user = User.objects.create_user("old", password="Str0ng-pass-123")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/api/analyses/").status_code, 404)
        self.assertEqual(self.client.get("/accounts/api/me/").status_code, 404)

    @mock.patch("analyses.tasks.predict_video", return_value=FAKE_RESPONSE)
    def test_create_returns_status_url_from_reverse(self, m):
        user = User.objects.create_user("su", password="Str0ng-pass-123")
        self.client.force_login(user)
        with override_settings(MEDIA_ROOT=TMP_MEDIA):
            res = self.client.post("/api/v1/analyses/", {"input_type": "UPLOAD", "video_file": mp4()})
        body = res.json()
        self.assertEqual(body["status_url"], f"/api/v1/analyses/{body['id']}/status/")

    def test_index_passes_api_urls_to_js(self):
        user = User.objects.create_user("js", password="Str0ng-pass-123")
        self.client.force_login(user)
        res = self.client.get("/")
        self.assertContains(res, 'data-list-url="/api/v1/analyses/"')
        self.assertContains(res, 'data-status-url="/api/v1/analyses/0/status/"')


class HealthTests(TestCase):
    """GET /api/v1/health/ : 로그인 없이 DB·Redis 상태. 실패하면 503."""

    @mock.patch("config.health._check_redis")
    def test_health_ok(self, redis_check):
        res = self.client.get("/api/v1/health/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["checks"]["db"]["ok"])
        self.assertTrue(body["checks"]["redis"]["ok"])

    @mock.patch("config.health._check_redis", side_effect=ConnectionError("down"))
    def test_health_redis_down_is_503(self, redis_check):
        res = self.client.get("/api/v1/health/")
        self.assertEqual(res.status_code, 503)
        self.assertFalse(res.json()["checks"]["redis"]["ok"])

    def test_health_post_not_allowed(self):
        self.assertEqual(self.client.post("/api/v1/health/").status_code, 405)


@override_settings(MEDIA_ROOT=TMP_MEDIA, PENDING_STALE_MINUTES=10)
class StuckJobTests(TestCase):
    """Redis·Worker가 없을 때 작업이 영원히 PENDING에 남지 않게 한다."""

    def setUp(self):
        self.user = User.objects.create_user("stuck", password="Str0ng-pass-123")
        self.client.force_login(self.user)

    @mock.patch("analyses.views.run_analysis.apply_async", side_effect=ConnectionRefusedError("redis down"))
    def test_enqueue_failure_saved_as_failure(self, apply_async):
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post("/api/v1/analyses/", {"input_type": "UPLOAD", "video_file": mp4()})
        job = AnalysisJob.objects.get()
        self.assertEqual(job.status, "FAILURE")
        self.assertIn("대기열", job.error_message)
        self.assertIsNotNone(job.finished_at)
        self.assertIn(res.status_code, (202, 503))  # 테스트는 트랜잭션 안이라 202, 실제 요청은 503

    @mock.patch("analyses.views.run_analysis.apply_async", side_effect=ConnectionRefusedError("redis down"))
    def test_enqueue_failure_returns_503_outside_transaction(self, apply_async):
        from rest_framework.test import APIRequestFactory, force_authenticate

        from .views import AnalysisJobViewSet

        req = APIRequestFactory().post("/api/v1/analyses/", {"input_type": "UPLOAD", "video_file": mp4()},
                                       format="multipart")
        force_authenticate(req, user=self.user)
        with mock.patch("analyses.views.transaction.on_commit", side_effect=lambda fn: fn()):
            res = AnalysisJobViewSet.as_view({"post": "create"})(req)
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.data["status"], "FAILURE")

    def _job(self, status, minutes_ago):
        job = AnalysisJob.objects.create(user=self.user, input_type="UPLOAD", status=status)
        past = timezone.now() - timedelta(minutes=minutes_ago)
        AnalysisJob.objects.filter(pk=job.pk).update(created_at=past, started_at=past)
        return AnalysisJob.objects.get(pk=job.pk)

    def test_fresh_pending_cannot_be_deleted(self):
        job = self._job("PENDING", 1)
        self.assertFalse(job.is_stale)
        self.assertEqual(self.client.delete(f"/api/v1/analyses/{job.pk}/").status_code, 409)

    def test_stale_pending_can_be_deleted(self):
        job = self._job("PENDING", 11)
        self.assertTrue(self.client.get(f"/api/v1/analyses/{job.pk}/status/").json()["is_stale"])
        self.assertEqual(self.client.delete(f"/api/v1/analyses/{job.pk}/").status_code, 204)
        self.assertFalse(AnalysisJob.objects.filter(pk=job.pk).exists())

    @override_settings(CELERY_TASK_TIME_LIMIT=600)
    def test_stale_started_can_be_deleted(self):
        self.assertEqual(self.client.delete(f"/api/v1/analyses/{self._job('STARTED', 5).pk}/").status_code, 409)
        self.assertEqual(self.client.delete(f"/api/v1/analyses/{self._job('STARTED', 12).pk}/").status_code, 204)


class PollingLimitTests(TestCase):
    @override_settings(POLL_TIMEOUT_SECONDS=120)
    def test_index_passes_poll_timeout_to_js(self):
        self.client.force_login(User.objects.create_user("poll", password="Str0ng-pass-123"))
        self.assertContains(self.client.get("/"), 'data-poll-timeout="120"')


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class JobLoggingTests(TestCase):
    """작업 1건을 로그로 추적: job id · 단계 · 걸린 시간, FastAPI에는 X-Job-ID 헤더."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        celery_app.conf.task_always_eager = True

    @classmethod
    def tearDownClass(cls):
        celery_app.conf.task_always_eager = False
        super().tearDownClass()

    def setUp(self):
        self.client.force_login(User.objects.create_user("logger", password="Str0ng-pass-123"))

    @mock.patch("analyses.tasks.predict_video", return_value=FAKE_RESPONSE)
    def test_success_logs_each_step_with_job_id(self, m):
        with self.assertLogs("analyses.tasks", level="INFO") as logs, self.captureOnCommitCallbacks(execute=True):
            job_id = self.client.post("/api/v1/analyses/", {"input_type": "UPLOAD", "video_file": mp4()}).json()["id"]
        text = "\n".join(logs.output)
        for step in ("시작", "영상 확보", "AI 추론 응답", "저장 완료 SUCCESS"):
            self.assertIn(f"job#{job_id} {step}", text)
        m.assert_called_once()
        self.assertEqual(m.call_args.kwargs["job_id"], job_id)

    @mock.patch("analyses.tasks.predict_video", side_effect=AIServiceError("AI 서버 오류(422): 영상을 열 수 없습니다"))
    def test_failure_logs_total_time(self, m):
        with self.assertLogs("analyses.tasks", level="INFO") as logs, self.captureOnCommitCallbacks(execute=True):
            job_id = self.client.post("/api/v1/analyses/", {"input_type": "UPLOAD", "video_file": mp4()}).json()["id"]
        self.assertTrue(any(f"job#{job_id} 실패 (총 " in line for line in logs.output))

    def test_services_sends_job_id_header(self):
        from .services import predict_video

        path = f"{TMP_MEDIA}/h.mp4"
        with open(path, "wb") as f:
            f.write(b"0" * 10)
        ok = mock.Mock(status_code=200)
        ok.json.return_value = FAKE_RESPONSE
        with mock.patch("analyses.services.requests.post", return_value=ok) as post:
            predict_video(path, job_id=7)
        self.assertEqual(post.call_args.kwargs["headers"], {"X-Job-ID": "7"})


class VisibleToTests(TestCase):
    """API와 화면이 같은 조회 규칙(AnalysisJob.objects.visible_to)을 쓰는지."""

    def setUp(self):
        self.owner = User.objects.create_user("owner", password="Str0ng-pass-123")
        self.other = User.objects.create_user("other", password="Str0ng-pass-123")
        self.staff = User.objects.create_user("staff", password="Str0ng-pass-123", is_staff=True)
        self.job = AnalysisJob.objects.create(user=self.owner, input_type="UPLOAD", status="SUCCESS")

    def test_visible_to(self):
        self.assertEqual(list(AnalysisJob.objects.visible_to(self.owner)), [self.job])
        self.assertEqual(list(AnalysisJob.objects.visible_to(self.other)), [])
        self.assertEqual(list(AnalysisJob.objects.visible_to(self.staff)), [self.job])

    def test_detail_page_and_api_follow_same_rule(self):
        for user, code in ((self.owner, 200), (self.other, 404), (self.staff, 200)):
            self.client.force_login(user)
            self.assertEqual(self.client.get(f"/analyses/{self.job.pk}/").status_code, code, user.username)
            self.assertEqual(self.client.get(f"/api/v1/analyses/{self.job.pk}/").status_code, code, user.username)


class QueryCountTests(TestCase):
    """폴링·Admin 목록이 작업·예측 수에 따라 쿼리가 늘어나지 않는지(N+1 방지)."""

    def setUp(self):
        self.staff = User.objects.create_superuser("root", password="Str0ng-pass-123")
        for i in range(5):
            job = AnalysisJob.objects.create(user=self.staff, input_type="UPLOAD", status="SUCCESS")
            for t in range(3):
                PersonPrediction.objects.create(job=job, track_id=t, action_label="wave", confidence=0.9)
        self.job = job
        self.client.force_login(self.staff)

    def test_status_poll_counts_without_loading_predictions(self):
        # 세션 · 사용자 · 작업+COUNT 1개 = 3쿼리 (예측 행을 따로 읽지 않음)
        with self.assertNumQueries(3):
            res = self.client.get(f"/api/v1/analyses/{self.job.pk}/status/")
        self.assertEqual(res.json()["prediction_count"], 3)

    def test_admin_changelist_does_not_grow_with_rows(self):
        url = "/admin/analyses/analysisjob/"
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as five:
            self.assertContains(self.client.get(url), "root")
        for i in range(5):
            AnalysisJob.objects.create(user=self.staff, input_type="UPLOAD", status="SUCCESS")
        with CaptureQueriesContext(connection) as ten:
            self.client.get(url)
        self.assertEqual(len(five.captured_queries), len(ten.captured_queries))
