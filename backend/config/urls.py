from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),                # 화면: 회원
    path("api/v1/", include("config.api_urls", namespace="api")),  # API는 여기 한 곳 (버전 v1)
    path("", include("analyses.urls")),                         # 화면: 분석
]

# 업로드·수집 영상(/media/). 개발·시연(DEBUG)에서만 Django가 직접 제공하고,
# 운영에서는 nginx 같은 웹 서버가 맡는다. 시연에서 DEBUG=False로 돌릴 때만 SERVE_MEDIA=True.
if settings.DEBUG or settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
