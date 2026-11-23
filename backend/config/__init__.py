# Django가 시작될 때 Celery 앱도 함께 불러와 @shared_task가 이 앱에 연결되게 한다.
from .celery import app as celery_app

__all__ = ("celery_app",)
