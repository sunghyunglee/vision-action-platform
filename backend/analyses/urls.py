"""analyses 앱의 화면(HTML) 주소. API 주소는 api_urls.py에 따로 둔다."""
from django.urls import path

from . import page_views

app_name = "analyses"

urlpatterns = [
    path("", page_views.index, name="index"),
    path("analyses/<int:pk>/", page_views.detail, name="detail"),
    path("dashboard/", page_views.dashboard, name="dashboard"),
]
