"""API는 이 파일 한 곳에 모은다. config/urls.py에서 /api/v1/ 접두사를 붙인다.

/api/v1/analyses/...   분석 작업 (analyses/api_urls.py)
/api/v1/auth/me/       로그인한 본인 정보
/api/v1/health/        DB·Redis 연결 확인 (로그인 불필요)
"""
from django.urls import include, path

from accounts import views as account_views

from . import health

app_name = "api"

urlpatterns = [
    path("", include("analyses.api_urls")),
    path("auth/me/", account_views.me, name="me"),
    path("health/", health.health, name="health"),
]
