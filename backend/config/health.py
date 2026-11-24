"""GET /api/v1/health/ : Django가 DB와 Redis(Celery 대기열)에 붙을 수 있는지 확인한다.

- 로그인 없이 호출 가능 (compose healthcheck · 모니터링용). 비밀 정보는 응답에 넣지 않는다.
- 둘 다 정상이면 200, 하나라도 실패하면 503 → docker compose ps 에서 unhealthy로 보인다.
"""
import logging
import time

import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger("analyses")


def _check_db():
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()


def _check_redis():
    client = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2, socket_timeout=2)
    try:
        client.ping()
    finally:
        client.close()


@require_GET
def health(request):
    checks = {}
    for name, fn in (("db", _check_db), ("redis", _check_redis)):
        t0 = time.monotonic()
        try:
            fn()
            checks[name] = {"ok": True, "ms": round((time.monotonic() - t0) * 1000, 1)}
        except Exception as e:  # 연결 실패 종류와 상관없이 '불통'으로 보고
            logger.warning("health: %s 실패 (%s)", name, type(e).__name__)
            checks[name] = {"ok": False, "error": type(e).__name__}
    ok = all(c["ok"] for c in checks.values())
    return JsonResponse({"status": "ok" if ok else "error", "checks": checks}, status=200 if ok else 503)
