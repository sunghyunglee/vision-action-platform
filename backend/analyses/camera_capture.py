"""허용된 IP Webcam에서 정해진 시간(기본 8초)만 프레임을 읽어 MP4로 저장하고 연결을 끊는다.

- 누가 읽나? Celery Worker (브라우저나 Django 요청 함수가 아님)
- 언제 끝나나? capture_seconds가 지나면 반복을 멈추고 release()
- 어떤 주소? settings.IP_WEBCAM_ALLOWED_URLS 안의 주소만. 사용자가 URL을 직접 입력하지 않는다.
"""
import logging
import time
from pathlib import Path

import cv2
from django.conf import settings

logger = logging.getLogger(__name__)


class CameraError(Exception):
    pass


def get_allowed_camera_url(index):
    cameras = settings.IP_WEBCAM_ALLOWED_URLS
    if index is None or not (0 <= index < len(cameras)):
        raise CameraError("허용 목록에 없는 카메라입니다.")
    return cameras[index]


def capture_clip(index, seconds, out_path, max_fps=30):
    """카메라 index에서 seconds초 동안 프레임을 모아 out_path(mp4)로 저장. 저장한 프레임 수를 반환."""
    url = get_allowed_camera_url(index)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, settings.CAMERA_CONNECT_TIMEOUT * 1000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, settings.CAMERA_CONNECT_TIMEOUT * 1000)
    if not cap.isOpened():
        cap.release()
        raise CameraError("카메라에 연결하지 못했습니다. 휴대폰 IP Webcam 앱이 켜져 있고 같은 네트워크인지 확인하세요.")

    writer = None
    frames = 0
    fail_streak = 0
    min_interval = 1.0 / max_fps
    start = time.monotonic()
    last = 0.0
    try:
        while time.monotonic() - start < seconds:
            ok, frame = cap.read()
            if not ok or frame is None:
                fail_streak += 1
                if fail_streak > 30:
                    raise CameraError("수집 중 카메라 연결이 끊겼습니다.")
                time.sleep(0.05)
                continue
            fail_streak = 0
            now = time.monotonic()
            if now - last < min_interval:  # MJPEG 스트림이 너무 빠르면 FPS 제한
                continue
            last = now
            if writer is None:
                h, w = frame.shape[:2]
                writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), max_fps, (w, h))
            writer.write(frame)
            frames += 1
    finally:
        cap.release()
        if writer is not None:
            writer.release()

    elapsed = time.monotonic() - start
    if frames == 0:
        raise CameraError("카메라에서 프레임을 하나도 받지 못했습니다.")
    # 실제로 받은 FPS로 다시 기록해 영상 길이가 실제 수집 시간과 맞도록 보정
    real_fps = max(1.0, frames / elapsed)
    if abs(real_fps - max_fps) > 1:
        _rewrite_fps(out_path, real_fps)
    logger.info("카메라 %s에서 %.1f초 동안 %d프레임 수집(%.1f fps)", index, elapsed, frames, real_fps)
    return frames


def _rewrite_fps(path, fps):
    tmp = path.with_suffix(".tmp.mp4")
    cap = cv2.VideoCapture(str(path))
    writer = None
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if writer is None:
            h, w = frame.shape[:2]
            writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        writer.write(frame)
    cap.release()
    if writer is not None:
        writer.release()
        tmp.replace(path)
