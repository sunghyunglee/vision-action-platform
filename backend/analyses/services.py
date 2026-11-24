"""FastAPI AI 서버에 영상을 HTTP(multipart)로 보내고 응답을 정리한다.

컨테이너끼리는 localhost가 아니라 Compose 서비스 이름(http://fastapi:8001)으로 통신한다.
FastAPI는 DB를 모르므로, 파일 경로가 아니라 파일 내용 자체를 전송한다.
"""
import logging
from pathlib import Path

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """AI 서버 호출 실패. 메시지는 사용자 화면에 그대로 보여 줄 수 있게 쓴다."""


def check_health():
    res = requests.get(f"{settings.AI_SERVICE_URL}/health", timeout=5)
    res.raise_for_status()
    return res.json()


def predict_video(path, job_id=None):
    """job_id를 X-Job-ID 헤더로 같이 보내 FastAPI 로그에서도 같은 작업을 찾을 수 있게 한다."""
    url = f"{settings.AI_SERVICE_URL}/predict/video"
    path = Path(path)
    headers = {"X-Job-ID": str(job_id)} if job_id is not None else {}
    try:
        with path.open("rb") as f:
            res = requests.post(
                url,
                files={"file": (path.name, f, "video/mp4")},
                headers=headers,
                timeout=(5, settings.AI_SERVICE_TIMEOUT),  # (연결, 응답) 타임아웃
            )
    except requests.Timeout as e:
        raise AIServiceError(f"AI 서버 응답 시간이 {settings.AI_SERVICE_TIMEOUT}초를 넘었습니다.") from e
    except requests.ConnectionError as e:
        raise AIServiceError("AI 서버(FastAPI)에 연결할 수 없습니다. fastapi 컨테이너 상태를 확인하세요.") from e

    if res.status_code >= 400:
        try:
            detail = res.json().get("detail", res.text)
        except ValueError:
            detail = res.text
        logger.warning("AI 서버 오류 %s: %s", res.status_code, detail)
        raise AIServiceError(f"AI 서버 오류({res.status_code}): {detail}")

    data = res.json()
    if "predictions" not in data:
        raise AIServiceError("AI 서버 응답 형식이 올바르지 않습니다(predictions 없음).")
    return data
