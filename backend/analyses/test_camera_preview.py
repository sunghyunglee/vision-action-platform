"""IP Webcam 실시간 미리보기 /cameras/<index>/stream/ 테스트 (Django가 MJPEG 중계).

카메라는 requests.get을 mock으로 바꿔서, 휴대폰 없이 돈다.
"""
from unittest import mock

import requests
from django.contrib.auth.models import User
from django.core.signals import request_finished
from django.db import close_old_connections
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .stream_views import camera_stream


class FakeMjpeg:
    """requests.get(stream=True) 대신 쓰는 가짜 카메라 응답."""

    def __init__(self, content_type="multipart/x-mixed-replace;boundary=frame", chunks=None, endless=False):
        self.headers = {"Content-Type": content_type}
        self.chunks = chunks if chunks is not None else [b"--frame\r\n", b"jpeg-1", b"--frame\r\n", b"jpeg-2"]
        self.endless = endless
        self.closed = False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=1):
        if self.endless:
            while True:
                yield b"--frame\r\njpeg"
        yield from self.chunks

    def close(self):
        self.closed = True


CAMERA_URL = "http://192.168.0.10:8080/video"


@override_settings(IP_WEBCAM_ALLOWED_URLS=[CAMERA_URL], CAMERA_PREVIEW_MAX_SECONDS=60)
class CameraPreviewTests(TestCase):
    """IP Webcam 실시간 미리보기 /cameras/<index>/stream/ (Django가 MJPEG 중계)."""

    def setUp(self):
        self.user = User.objects.create_user("viewer", password="Str0ng-pass-123")

    def login(self):
        self.client.login(username="viewer", password="Str0ng-pass-123")

    def test_url(self):
        self.assertEqual(reverse("analyses:camera_stream", args=[0]), "/cameras/0/stream/")

    def test_login_required(self):
        res = self.client.get("/cameras/0/stream/")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/accounts/login/", res["Location"])

    def test_camera_not_in_allow_list_404(self):
        self.login()
        self.assertEqual(self.client.get("/cameras/5/stream/").status_code, 404)

    @mock.patch("analyses.stream_views.requests.get")
    def test_relays_mjpeg_and_closes_camera(self, get):
        fake = FakeMjpeg()
        get.return_value = fake
        self.login()
        with self.assertLogs("analyses", level="INFO") as logs:
            res = self.client.get("/cameras/0/stream/")
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.streaming)
            self.assertEqual(res["Content-Type"], "multipart/x-mixed-replace;boundary=frame")
            self.assertEqual(res["Cache-Control"], "no-store")
            body = b"".join(res.streaming_content)
        self.assertEqual(body, b"--frame\r\njpeg-1--frame\r\njpeg-2")
        self.assertTrue(fake.closed)
        self.assertEqual(get.call_args.args[0], CAMERA_URL)  # 허용 목록 주소로만 연결
        self.assertTrue(get.call_args.kwargs["stream"])
        text = "\n".join(logs.output)
        self.assertIn("미리보기 시작", text)
        self.assertIn("미리보기 종료", text)
        self.assertNotIn("192.168", text)

    @override_settings(CAMERA_PREVIEW_MAX_SECONDS=0)
    @mock.patch("analyses.stream_views.requests.get")
    def test_stops_after_max_seconds(self, get):
        fake = FakeMjpeg(endless=True)
        get.return_value = fake
        self.login()
        res = self.client.get("/cameras/0/stream/")
        chunks = list(res.streaming_content)  # 끝없는 카메라여도 시간 제한으로 끝나야 함
        self.assertEqual(len(chunks), 1)
        self.assertTrue(fake.closed)

    @mock.patch("analyses.stream_views.requests.get")
    def test_browser_disconnect_closes_camera(self, get):
        fake = FakeMjpeg(endless=True)
        get.return_value = fake
        # 테스트 클라이언트 대신 뷰를 직접 부른다. 테스트 클라이언트는 스트리밍 응답을 감싸서,
        # close() 도중에 close_old_connections 신호를 다시 붙여 버린다.
        request = RequestFactory().get("/cameras/0/stream/")
        request.user = self.user
        res = camera_stream(request, 0)
        next(iter(res))
        # 브라우저가 끊기면 WSGI 서버가 response.close()를 부른다. close()는 request_finished 신호로
        # close_old_connections도 부르는데, 테스트 트랜잭션 안에서는 PostgreSQL 연결이 실제로 닫혀
        # 뒤 테스트가 모두 깨진다(SQLite 메모리 DB는 닫히지 않아서 통과했던 것). 그 동안만 신호를 떼어 둔다.
        request_finished.disconnect(close_old_connections)
        try:
            with self.assertLogs("analyses", level="INFO") as logs:
                res.close()
        finally:
            request_finished.connect(close_old_connections)
        self.assertTrue(fake.closed)
        self.assertIn("브라우저 종료", "\n".join(logs.output))

    @mock.patch("analyses.stream_views.requests.get")
    def test_camera_down_502_without_address(self, get):
        get.side_effect = requests.ConnectionError(f"cannot connect {CAMERA_URL}")
        self.login()
        res = self.client.get("/cameras/0/stream/")
        self.assertEqual(res.status_code, 502)
        self.assertNotIn("192.168", res.content.decode())

    @mock.patch("analyses.stream_views.requests.get")
    def test_not_mjpeg_502(self, get):
        fake = FakeMjpeg(content_type="text/html")
        get.return_value = fake
        self.login()
        res = self.client.get("/cameras/0/stream/")
        self.assertEqual(res.status_code, 502)
        self.assertTrue(fake.closed)

    def test_index_has_preview_without_camera_address(self):
        self.login()
        html = self.client.get("/").content.decode()
        self.assertIn('data-stream-url="/cameras/0/stream/"', html)
        self.assertIn('data-max-seconds="60"', html)
        self.assertIn('id="preview-img"', html)
        self.assertNotIn("192.168", html)
        self.assertNotIn(":8080", html)

    @override_settings(IP_WEBCAM_ALLOWED_URLS=[])
    def test_no_preview_without_cameras(self):
        self.login()
        self.assertNotIn('id="camera-preview"', self.client.get("/").content.decode())
