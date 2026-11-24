"""analyses 앱의 API 주소 (DRF Router). 접두사 /api/v1/ 은 config/api_urls.py에서 붙인다.

GET/POST          analyses/
GET/PATCH/DELETE  analyses/<id>/
GET               analyses/<id>/status/
"""
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("analyses", views.AnalysisJobViewSet, basename="analysis")

urlpatterns = router.urls
