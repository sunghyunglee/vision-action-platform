"""과제 기능 테스트(T05~T09 중 웹 서버에서 확인 가능한 부분).

FastAPI·Redis 없이 돌도록 Celery는 eager 모드, AI 호출은 mock으로 대체한다.
실행: python manage.py test
"""
import shutil
import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

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
