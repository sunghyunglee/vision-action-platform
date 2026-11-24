"""IP Webcam 실시간 미리보기: Django가 허용 목록 카메라의 MJPEG 스트림을 그대로 중계한다.

- 주소: /cameras/<index>/stream/ (화면용, 로그인 필요. JSON API가 아니라서 /api/v1/ 밑에 두지 않음)
- 브라우저는 휴대폰 주소에 직접 붙지 않는다 → 카메라 IP가 HTML·캡처에 나오지 않고, 허용 목록 규칙도 그대로
- 디코딩 없이 바이트만 넘긴다(JPEG 재압축 없음, CPU 거의 안 씀)
- gunicorn 동기 워커를 붙잡으므로 CAMERA_PREVIEW_MAX_SECONDS(기본 60초)가 지나면 서버가 먼저 끊는다
- 분석 수집(Celery capture_clip)과는 별개 연결이다. 분석 흐름 Django → Redis → Celery → FastAPI는 그대로
"""
import logging
import time

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET

from .camera_capture import CAMERA_CONNECT_FAILED, CameraError, get_allowed_camera_url

logger = logging.getLogger("analyses")

CHUNK_SIZE = 16 * 1024


def _error(text, status=502):
    # 오류 문구에도 카메라 주소를 넣지 않는다
    return HttpResponse(text, status=status, content_type="text/plain; charset=utf-8")


def _relay(upstream, index, username, max_seconds):
    """카메라 응답 바이트를 max_seconds 동안만 흘려보낸다. 브라우저가 끊거나 시간이 다 되면 카메라 연결도 닫는다."""
    started = time.monotonic()
    sent = 0
    reason = "시간 제한"
    try:
        for chunk in upstream.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                sent += len(chunk)
                yield chunk
            if time.monotonic() - started >= max_seconds:
                break
        else:
            reason = "카메라 스트림 끝"
    except GeneratorExit:  # 브라우저가 연결을 끊음(탭 이동·창 닫기)
        reason = "브라우저 종료"
        raise
    except requests.RequestException as exc:
        reason = f"카메라 읽기 실패({type(exc).__name__})"
    finally:
        upstream.close()
        logger.info("카메라 %s 미리보기 종료 user=%s %.1fs %dKB (%s)",
                    index, username, time.monotonic() - started, sent // 1024, reason)


@login_required
@require_GET
def camera_stream(request, index):
    try:
        url = get_allowed_camera_url(index)
    except CameraError:
        raise Http404("허용 목록에 없는 카메라입니다.")

    timeout = settings.CAMERA_CONNECT_TIMEOUT
    try:
        upstream = requests.get(url, stream=True, timeout=(timeout, timeout))
        upstream.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("카메라 %s 미리보기 연결 실패: %s", index, type(exc).__name__)
        return _error(CAMERA_CONNECT_FAILED)

    content_type = upstream.headers.get("Content-Type", "")
    if not content_type.lower().startswith("multipart/x-mixed-replace"):
        upstream.close()
        logger.warning("카메라 %s 미리보기: MJPEG가 아님 (%s)", index, content_type or "Content-Type 없음")
        return _error("카메라 주소가 MJPEG 스트림이 아닙니다. IP Webcam의 /video 주소를 허용 목록에 넣으세요.")

    logger.info("카메라 %s 미리보기 시작 user=%s", index, request.user.username)
    response = StreamingHttpResponse(
        _relay(upstream, index, request.user.username, settings.CAMERA_PREVIEW_MAX_SECONDS),
        content_type=content_type,  # boundary 값을 그대로 넘겨야 브라우저가 프레임을 나눈다
    )
    response["Cache-Control"] = "no-store"
    response["X-Accel-Buffering"] = "no"  # 앞단에 프록시가 생겨도 버퍼링하지 않게
    return response
