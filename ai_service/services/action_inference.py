"""사람별 (시각, Feature) 목록 → 5초 Window → 30 Step → RandomForest → Track ID별 Action·Confidence.

7~8일차 실시간 추론과 같은 규칙을 저장 영상에 그대로 적용한다 (src/realtime_utils.py 재사용).
- TimedFeatureBuffer: 최근 window_seconds(5초) 동안의 Feature만 유지
- is_ready: Window가 80% 이상 차고, 유효 Feature 비율 60% 이상, 10개 이상일 때만 예측
- predict_from_window: 유효 Feature를 시간축 기준 30 Step으로 보간(resample) → 1,140개로 펼쳐 predict_proba
- prediction_interval_sec(0.25초)마다 한 번 예측, PredictionStabilizer로 다수결 Label도 계산

영상이 짧아 5초 Window가 한 번도 안 차면, 6일차 학습과 같은 방식(보인 구간 전체를 30 Step으로 보간,
유효 프레임 10개 이상)으로 1번 예측한다 → mode "whole_track".

최종 결과: 한 사람의 모든 Window 확률을 평균해 가장 높은 Action과 그 확률(confidence)을 고른다.
"""
import numpy as np

from src.realtime_utils import PredictionStabilizer, TimedFeatureBuffer, predict_from_window
from src.sequence_utils import flatten_sequence, resample_sequence


def _predict_track(model, items, cfg):
    rt, mp = cfg["day07_realtime"], cfg["day08_multi_person"]
    steps = int(cfg["day06_baseline"]["sequence_steps"])
    buffer = TimedFeatureBuffer(rt["window_seconds"])
    stabilizer = PredictionStabilizer(rt["stabilization_buffer"], rt["stabilization_min_votes"])
    probs, stable_label, last_pred_t, prev_t = [], "WARMING_UP", -1e9, None

    for t, feat in items:
        # 8일차 lost_timeout: 오래 안 보이다 다시 나타나면 상태를 새로 시작
        if prev_t is not None and t - prev_t > mp["lost_timeout_seconds"]:
            buffer.clear()
            stabilizer.clear()
        prev_t = t
        buffer.append(t, feat)
        ready = buffer.is_ready(rt["min_window_fill_ratio"], rt["min_valid_feature_ratio"],
                                rt["min_valid_features"])
        if ready and t - last_pred_t >= rt["prediction_interval_sec"]:
            threshold_label, _raw, _conf, p = predict_from_window(
                model, buffer, steps, rt["confidence_threshold"])
            probs.append(p)
            stable_label = stabilizer.update(threshold_label)
            last_pred_t = t

    if probs:
        return np.asarray(probs), "window", stable_label

    # 짧은 영상: 6일차 학습 방식으로 보인 구간 전체를 30 Step으로
    valid = [(t, f) for t, f in items if f is not None]
    if len(valid) < int(cfg["day06_baseline"]["min_valid_frames"]):
        return None, None, None
    times = np.asarray([t for t, _ in valid], dtype=np.float32)
    matrix = np.stack([f for _, f in valid])
    try:
        seq = resample_sequence(matrix, times, target_steps=steps)
    except ValueError:
        return None, None, None
    p = model.predict_proba(flatten_sequence(seq).reshape(1, -1))[0]
    return p.reshape(1, -1), "whole_track", None


def predict_tracks(action_model, tracks, cfg):
    model = action_model.model
    classes = [str(c) for c in model.classes_]  # 확률 열 순서 = model.classes_ 순서
    results = []
    for tr in tracks:
        probs, mode, stable = _predict_track(model, tr["items"], cfg)
        if probs is None:
            continue  # 유효 프레임이 너무 적은 사람은 예측하지 않는다
        mean = probs.mean(axis=0)
        best = int(mean.argmax())
        results.append({
            "track_id": int(tr["track_id"]),
            "action_label": classes[best],
            "confidence": round(float(mean[best]), 4),
            "windows": int(len(probs)),               # PM 계약 키: 예측에 쓴 Window 수
            "frame_count": int(tr["frame_count"]),    # 이 사람의 유효 Feature 프레임 수
            "mode": mode,                             # window(5초 Window) / whole_track(짧은 영상)
            "stable_label": stable,                   # 마지막 다수결 Label (UNKNOWN 가능, 참고용)
            "probabilities": {c: round(float(v), 4) for c, v in zip(classes, mean)},
        })
    return results
