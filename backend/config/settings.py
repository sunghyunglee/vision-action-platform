"""
vision_action_platform Django 설정.

값은 환경변수(.env → compose.yaml의 env_file)에서 읽는다.
환경변수가 없으면 로컬 개발용 기본값(SQLite, Redis localhost)을 쓴다.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 설치 패키지
    "rest_framework",
    # 직접 만든 앱 2개
    "accounts",
    "analyses",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # DEBUG=False에서도 CSS·JS 제공
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── DB: POSTGRES_HOST가 있으면 PostgreSQL, 없으면 로컬 SQLite ──
if os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "vision_action"),
            "USER": os.environ.get("POSTGRES_USER", "vision"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

# ── 정적 파일(CSS·JS)과 업로드 영상(Media) ──
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic 결과
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
# DEBUG=False에서도 Django가 /media/를 직접 제공할지(시연용). 운영은 False + 웹 서버가 제공
SERVE_MEDIA = env_bool("SERVE_MEDIA", False)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── 로그인 ──
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "analyses:index"
LOGOUT_REDIRECT_URL = "login"

# ── DRF: 세션 로그인 사용(템플릿 화면과 같은 로그인 상태 공유) ──
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# ── 업로드 제한 ──
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "100"))
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 이보다 큰 파일은 임시파일로 받음
ALLOWED_VIDEO_EXTENSIONS = ["mp4", "mov", "avi", "mkv"]

# ── Redis · Celery ──
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "600"))
CELERY_TASK_SOFT_TIME_LIMIT = CELERY_TASK_TIME_LIMIT - 30
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)  # Redis 없이 테스트할 때만 True
# Redis가 꺼져 있을 때 작업 등록이 오래 매달리지 않게: 연결 3초, 재시도 2번
CELERY_BROKER_CONNECTION_TIMEOUT = 3
CELERY_TASK_PUBLISH_RETRY_POLICY = {"max_retries": 2, "interval_start": 0, "interval_step": 0.5, "interval_max": 1}
CELERY_REDIS_SOCKET_CONNECT_TIMEOUT = 3
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {  # 결과 저장소(Redis) 재연결도 기본 20번 → 2번
    "retry_policy": {"max_retries": 2, "interval_start": 0, "interval_step": 0.5, "interval_max": 1},
}

# 이 시간(분)이 지나도 PENDING이면 Worker가 못 가져간 '멈춘 작업'으로 보고 삭제를 허용한다
PENDING_STALE_MINUTES = int(os.environ.get("PENDING_STALE_MINUTES", "10"))

# 분석 화면(analyses.js)이 상태를 조회하는 최대 시간(초). 넘으면 조회를 멈추고 안내 문구를 보여 준다
POLL_TIMEOUT_SECONDS = int(os.environ.get("POLL_TIMEOUT_SECONDS", "600"))

# ── FastAPI AI 서버 (컨테이너끼리는 서비스 이름 fastapi 로 접근) ──
AI_SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://localhost:8001")
AI_SERVICE_TIMEOUT = int(os.environ.get("AI_SERVICE_TIMEOUT", "300"))

# ── IP Webcam: 허용한 카메라만, 정해진 시간만 수집 ──
# 예) IP_WEBCAM_ALLOWED_URLS=http://192.168.0.23:8080/video
IP_WEBCAM_ALLOWED_URLS = env_list("IP_WEBCAM_ALLOWED_URLS", "")
CAMERA_CAPTURE_SECONDS = int(os.environ.get("CAMERA_CAPTURE_SECONDS", "8"))
CAMERA_CONNECT_TIMEOUT = int(os.environ.get("CAMERA_CONNECT_TIMEOUT", "10"))
# 웹캠 탭 실시간 미리보기(/cameras/<index>/stream/) 한 번의 최대 시간. gunicorn 워커를 오래 붙잡지 않게
CAMERA_PREVIEW_MAX_SECONDS = int(os.environ.get("CAMERA_PREVIEW_MAX_SECONDS", "60"))

# 이 값보다 낮은 confidence는 화면에 '판단 불확실'로 표시
LOW_CONFIDENCE_THRESHOLD = float(os.environ.get("LOW_CONFIDENCE_THRESHOLD", "0.55"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    # 시각 뒤에 +0900을 붙여 어느 시간대인지 로그만 보고 알 수 있게 한다(F7). DB 저장은 USE_TZ=True로 UTC 그대로
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{", "datefmt": "%Y-%m-%d %H:%M:%S %z"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    # propagate False: Celery Worker가 root 로거에도 출력해서 같은 줄이 두 번 찍히는 것을 막는다
    "loggers": {"analyses": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
