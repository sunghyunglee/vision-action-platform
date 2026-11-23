"""영상 → YOLO Pose·Tracking → 사람(Track ID)별 시간순 Feature 목록.

처리 순서 (영상 1건)
1. OpenCV로 영상이 열리는지·프레임이 있는지 확인 (실패 → VideoReadError → 422)
2. YOLO Pose + ByteTrack으로 프레임마다 사람별 Keypoint(COCO 17개)와 Track ID 추출
   (8일차 49_ip_webcam_multi_person_action.py의 model.track() 설정과 동일)
3. 사람마다 38차원 Frame Feature 계산 → src.multi_person_utils.feature_from_keypoints (8일차 원본 그대로)
4. Track ID별로 (영상 시각, Feature) 를 모은다. 이번 프레임에 안 보인 사람은 (시각, None)을 넣는다
   (8일차 MultiPersonStateManager.mark_missing과 같은 규칙, lost_timeout이 지나면 더 넣지 않음)

30 Step Sequence로 바꾸고 RandomForest에 넣는 일은 action_inference.py가 한다.
YOLO 모델은 서버 시작 시 한 번만 로드한다. Tracker 상태는 영상마다 새로 시작한다(persist=False).
"""
import logging
import os
import threading
from collections import defaultdict
from pathlib import Path

import cv2

from src.multi_person_utils import feature_from_keypoints

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = Path(os.environ.get("MODEL_DIR", BASE_DIR / "models"))


class VideoReadError(ValueError):
    """영상 파일 자체를 읽을 수 없음 (손상·코덱 문제·프레임 0개)."""


class PosePipeline:
    def __init__(self, config):
        from ultralytics import YOLO  # torch 로딩이 무거워서 여기서 import

        weights = os.environ.get("POSE_WEIGHTS") or config["pose_model"]
        path = Path(weights) if Path(weights).is_absolute() else MODEL_DIR / weights
        if not path.exists():
            raise FileNotFoundError(f"YOLO Pose 가중치가 없습니다: {path}")
        self.weights_name = path.name
        self.model = YOLO(str(path))
        self.imgsz = int(config["image_size"])
        self.conf = float(os.environ.get("POSE_CONF") or config["person_confidence"])
        self.device = os.environ.get("POSE_DEVICE") or config.get("device", "cpu")
        self.tracker = config["day08_multi_person"]["tracker"]
        self.lost_timeout = float(config["day08_multi_person"]["lost_timeout_seconds"])
        self.max_seconds = float(os.environ.get("MAX_VIDEO_SECONDS", "60"))  # 너무 긴 영상 방지
        # YOLO Tracker는 모델 객체에 상태를 저장하므로 영상 1건씩 순서대로 처리
        self._lock = threading.Lock()
        logger.info("Pose 모델 로드: %s (imgsz=%d, conf=%.2f, tracker=%s)",
                    self.weights_name, self.imgsz, self.conf, self.tracker)

    # ── 1. 영상 검사 ─────────────────────────────────────────
    @staticmethod
    def probe_video(path):
        cap = cv2.VideoCapture(str(path))
        try:
            if not cap.isOpened():
                raise VideoReadError("영상을 열 수 없습니다(손상되었거나 지원하지 않는 코덱).")
            ok, frame = cap.read()
            if not ok or frame is None:
                raise VideoReadError("영상에서 프레임을 읽을 수 없습니다.")
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            h, w = frame.shape[:2]
        finally:
            cap.release()
        return {"fps": round(fps, 2), "frames": frames, "width": w, "height": h,
                "duration_sec": round(frames / fps, 2) if fps else None}

    # ── 2~4. Pose·Tracking → 사람별 (시각, Feature) ───────────
    def process_video(self, path):
        video = self.probe_video(path)
        # 실시간(8일차)은 벽시계 시간을 썼지만, 저장된 영상은 '영상 속 시각' = 프레임 번호 / FPS
        fps = video["fps"] if video["fps"] > 0 else 30.0

        items = defaultdict(list)   # track_id → [(시각, 38차원 Feature 또는 None), ...]
        last_seen = {}              # track_id → 마지막으로 보인 시각
        frame_idx = 0

        with self._lock:
            results = self.model.track(
                source=str(path), stream=True, persist=False, tracker=self.tracker,
                imgsz=self.imgsz, conf=self.conf, device=self.device, verbose=False,
            )
            for r in results:
                t = frame_idx / fps
                frame_idx += 1
                if t > self.max_seconds:
                    break
                seen = set()
                boxes, kps = r.boxes, r.keypoints
                if boxes is not None and boxes.id is not None and kps is not None and kps.xy is not None:
                    ids = boxes.id.detach().cpu().numpy().astype(int)
                    kp_xy = kps.xy.detach().cpu().numpy()     # (사람 수, 17, 2) 픽셀 좌표
                    for i in range(min(len(ids), len(kp_xy))):
                        tid = int(ids[i])
                        seen.add(tid)
                        last_seen[tid] = t
                        items[tid].append((t, feature_from_keypoints(kp_xy[i])))
                # 안 보인 사람: lost_timeout 안이면 빈칸(None)으로 기록 → 유효 비율 계산에 반영
                for tid, ts in last_seen.items():
                    if tid not in seen and t - ts <= self.lost_timeout:
                        items[tid].append((t, None))

        video["analyzed_frames"] = frame_idx
        tracks = [{"track_id": tid, "items": items[tid],
                   "frame_count": sum(f is not None for _, f in items[tid])}
                  for tid in sorted(items)]
        return {"video": video, "tracks": tracks}
