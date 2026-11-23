"""6일차 학습 산출물 3개를 서버 시작 시 한 번만 로드하고 검사한다.

- rf_action_baseline.joblib : RandomForest 분류기 (영상이 아니라 1,140개 숫자를 입력받음)
- rf_feature_columns.json   : 학습 때 쓴 Feature 이름과 '순서' (30 Step × 38 Feature)
- rf_training_info.json     : sequence_steps, Class 목록 등 학습 정보

joblib.load()는 직접 만든 신뢰 가능한 파일에만 사용한다(pickle 기반이라 임의 코드 실행 위험).
"""
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import joblib

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = Path(os.environ.get("MODEL_DIR", BASE_DIR / "models"))

EXPECTED_CLASSES = {"bend_return", "leg_raise_lower", "walk_turn_walk", "drink_return", "sit_stand", "wave"}


class ModelNotReady(RuntimeError):
    pass


def load_project_config(path=None):
    """project.json: 원본 프로젝트의 Pose 설정 + 6·7·8일차 설정값(sequence_steps, Window 5초 등)을 그대로 옮긴 파일."""
    path = Path(path or os.environ.get("PROJECT_CONFIG", BASE_DIR / "project.json"))
    if not path.exists():
        raise ModelNotReady(f"설정 파일이 없습니다: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class ActionModel:
    model: object
    feature_columns: list
    training_info: dict
    classes: list
    sequence_steps: int
    feature_dim: int
    n_features: int
    files: dict = field(default_factory=dict)

    def summary(self):
        return {
            "classes": self.classes,
            "sequence_steps": self.sequence_steps,
            "feature_dim": self.feature_dim,
            "n_features": self.n_features,
            "files": self.files,
        }


def _find_info(info, *keys, default=None):
    for k in keys:
        if k in info:
            return info[k]
    return default


def load_action_model(model_dir=MODEL_DIR):
    model_dir = Path(model_dir)
    paths = {
        "model": model_dir / os.environ.get("RF_MODEL_FILE", "rf_action_baseline.joblib"),
        "columns": model_dir / os.environ.get("RF_COLUMNS_FILE", "rf_feature_columns.json"),
        "info": model_dir / os.environ.get("RF_INFO_FILE", "rf_training_info.json"),
    }
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise ModelNotReady(f"모델 파일이 없습니다: {', '.join(missing)} (README의 '모델 준비' 참고)")

    model = joblib.load(paths["model"])
    columns = json.loads(paths["columns"].read_text(encoding="utf-8"))
    if isinstance(columns, dict):  # {"feature_columns": [...]} 형태도 허용
        columns = _find_info(columns, "feature_columns", "columns", default=list(columns.values())[0])
    info = json.loads(paths["info"].read_text(encoding="utf-8"))

    classes = [str(c) for c in getattr(model, "classes_", [])]
    steps = int(_find_info(info, "sequence_steps", "seq_len", "steps", default=30))
    n_features = len(columns)

    # ── 규격 검사: 하나라도 어긋나면 서버가 '준비 안 됨'으로 뜨게 한다 ──
    n_in = getattr(model, "n_features_in_", n_features)
    if n_in != n_features:
        raise ModelNotReady(f"모델 입력 차원({n_in})과 Feature 목록 길이({n_features})가 다릅니다.")
    if n_features % steps:
        raise ModelNotReady(f"Feature 수 {n_features}가 sequence_steps {steps}로 나누어떨어지지 않습니다.")
    # Feature '순서' 검사: 원본 src/sequence_utils.py가 만드는 이름 순서(t00_nose_x ... t29_right_knee_angle)와 같아야 함
    from src.sequence_utils import sequence_feature_names
    if list(columns) != sequence_feature_names(steps):
        raise ModelNotReady("rf_feature_columns.json 순서가 src/sequence_utils.py의 Feature 순서와 다릅니다.")
    if set(classes) != EXPECTED_CLASSES:
        raise ModelNotReady(f"모델 Class가 6개 Action과 다릅니다: {classes}")

    am = ActionModel(
        model=model, feature_columns=columns, training_info=info, classes=classes,
        sequence_steps=steps, feature_dim=n_features // steps, n_features=n_features,
        files={k: p.name for k, p in paths.items()},
    )
    logger.info("Action 모델 로드: %d classes, %d steps × %d = %d features",
                len(classes), steps, am.feature_dim, n_features)
    return am


if __name__ == "__main__":
    # T01 확인용: python -m services.model_loader
    m = load_action_model()
    print(json.dumps(m.summary(), ensure_ascii=False, indent=2))
