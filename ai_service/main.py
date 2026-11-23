"""FastAPI AI 추론 서버.

- DB·회원 기능 없음. 영상을 받아 사람별 동작 예측 JSON만 돌려준다.
- 모델은 서버 시작 시 한 번 로드해 app.state에 두고 모든 요청에서 재사용한다.
실행: uvicorn main:app --host 0.0.0.0 --port 8001
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from routers import predictions
from services.model_loader import ModelNotReady, load_action_model, load_project_config
from services.pose_pipeline import PosePipeline

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ai_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.action_model = None
    app.state.pose = None
    app.state.load_error = None
    app.state.config = None
    try:
        app.state.config = load_project_config()
        app.state.action_model = load_action_model()
        app.state.pose = PosePipeline(app.state.config)
    except (ModelNotReady, FileNotFoundError, ImportError) as e:
        # 서버는 띄우고 /health에서 원인을 보여 준다(컨테이너가 재시작 루프에 빠지지 않게)
        app.state.load_error = str(e)
        logger.error("모델 준비 실패: %s", e)
    yield


app = FastAPI(title="Vision Action AI Service", version="1.0.0", lifespan=lifespan)
app.include_router(predictions.router)


@app.get("/health", tags=["health"])
def health():
    am = app.state.action_model
    ready = am is not None and app.state.pose is not None
    # PM 계약: {status, model_loaded, classes, n_features} (+ 확인용 정보)
    return {
        "status": "ok" if ready else "degraded",
        "model_loaded": ready,
        "classes": am.classes if am else [],
        "n_features": am.n_features if am else None,
        "sequence_steps": am.sequence_steps if am else None,
        "feature_dim": am.feature_dim if am else None,
        "pose_model": app.state.pose.weights_name if app.state.pose else None,
        "error": app.state.load_error,
    }
