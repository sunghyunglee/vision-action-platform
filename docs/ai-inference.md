# AI Inference

> 기준 코드: `ai_service/` (40d3916) · 모델은 별도 학습 프로젝트 [yolo-pose-action-recognition-project](https://github.com/sunghyunglee/yolo-pose-action-recognition-project) 의 결과를 **다시 학습하지 않고** 그대로 씁니다.
> 그림: [images/pipeline.png](images/pipeline.png) ④ 추론 칸

## 1. 모델 파일

| 파일 | 위치 | Git | 역할 |
|---|---|---|---|
| `rf_action_baseline.joblib` | `ai_service/models/` | 제외 | RandomForest (n_estimators 300 · random_state 42) · 6개 동작 |
| `yolo11n-pose.pt` | `ai_service/models/` | 제외 | YOLO11 Pose · 사람마다 COCO 관절 17개 |
| `rf_feature_columns.json` | `ai_service/models/` | 포함 | 입력 1,140개 열 순서 (`t00_nose_x` … `t29_right_knee_angle`) |
| `rf_training_info.json` | `ai_service/models/` | 포함 | `train_clips 6` · `subjects ["S01"]` · `feature_count 1140` · `sequence_steps 30` · classes 6 |
| `project.json` | `ai_service/` | 포함 | Pose · Window · Tracker 설정 (아래 표) |

compose 는 `./ai_service/models` 를 `/app/models` 에 **읽기 전용**으로 연결합니다. 모델을 이미지에 굽지 않아 파일만 바꿔 다시 시작하면 됩니다.

### 기동 시 검증 (`services/model_loader.py` `load_action_model()`)

| 검사 | 실패하면 |
|---|---|
| 파일 3개 존재 | `ModelNotReady("모델 파일이 없습니다: …")` |
| `n_features_in_` = 열 개수 (1,140) | 입력 차원 불일치 |
| 1,140 % `sequence_steps`(30) = 0 → `feature_dim` 38 | 나누어떨어지지 않음 |
| 열 순서 = `src/sequence_utils.py` `sequence_feature_names(30)` | 순서 다름 |
| `classes_` = 6개 `EXPECTED_CLASSES` | Class 다름 |

실패해도 서버는 죽지 않습니다. `GET /health` 가 `status: "degraded"` 와 이유를 보여 주고 `POST /predict/video` 는 503 을 돌려줍니다 → Celery 가 작업을 FAILURE + 이유로 저장합니다.

## 2. 설정 (`ai_service/project.json` · `.env`)

| 키 | 값 | 쓰는 곳 |
|---|---|---|
| `pose_model` · `image_size` · `person_confidence` | `yolo11n-pose.pt` · 640 · 0.25 | `PosePipeline` (`.env` `POSE_WEIGHTS` · `POSE_DEVICE=cpu`) |
| `day06_baseline.sequence_steps` · `min_valid_frames` | 30 · 10 | 보간 단계 · 짧은 영상 기준 |
| `day07_realtime.window_seconds` | 5.0 | `TimedFeatureBuffer` 길이 |
| `day07_realtime.min_window_fill_ratio` · `min_valid_feature_ratio` · `min_valid_features` | 0.8 · 0.6 · 10 | `is_ready()` 조건 |
| `day07_realtime.prediction_interval_sec` | 0.25 | Window 예측 간격 |
| `day07_realtime.confidence_threshold` | 0.55 | `stable_label` 계산 (참고용) |
| `day08_multi_person.tracker` · `lost_timeout_seconds` | `bytetrack.yaml` · 2.0 | 추적 · 오래 안 보이면 버퍼 초기화 |
| 환경 변수 `MAX_VIDEO_SECONDS` (기본값, `.env.example` 에는 없음) | 60 | 이보다 긴 영상은 앞부분만 분석 (`pose_pipeline.py:47`) |

(키 이름은 학습 프로젝트의 설정 파일 이름을 그대로 쓴 것입니다.)

## 3. 추론 단계

```text
mp4 ─▶ YOLO Pose + ByteTrack ─▶ keypoints (사람, 17, 2) ─▶ 사람마다 38-D ─▶ 5초 Window ─▶ (30, 38) ─▶ (1, 1140) ─▶ RandomForest
       pose_pipeline.py:72      model.track() :82          multi_person_utils:11   TimedFeatureBuffer   resample     flatten       predict_proba
```

| 단계 | 함수 (파일 : 줄) | 입력 → 출력 |
|---|---|---|
| ① 영상 읽기 · 추적 | `PosePipeline.process_video()` (`services/pose_pipeline.py:72`) · `model.track(stream=True, persist=False, tracker=bytetrack.yaml)` | mp4 → 프레임마다 Track ID · 관절 좌표. 영상마다 Tracker 를 새로 시작 |
| ② 38-D Frame Feature | `feature_from_keypoints(kp)` (`src/multi_person_utils.py:11`) | (17, 2) → 38 = `normalize_by_shoulder_width` 34 (엉덩이 중심 · 어깨 너비로 나눔) + `selected_joint_angles` 4 (팔꿈치 · 무릎). 모양이 안 맞으면 `None` |
| ③ Window | `TimedFeatureBuffer(5.0)` · `is_ready(0.8, 0.6, 10)` | 사람마다 최근 5초. 80% 이상 차고, 유효 비율 60% 이상, 10개 이상일 때만 |
| ④ 30 Step 보간 · 펼치기 | `predict_from_window()` → `resample_sequence()` · `flatten_sequence()` (`src/sequence_utils.py:30` · `:119`) | 유효 Feature → (30, 38) → (1, 1140) |
| ⑤ 예측 | `model.predict_proba()` (0.25초마다) | 6개 확률 |
| ⑥ 사람별 집계 | `predict_tracks()` (`services/action_inference.py:60`) | Window 확률 평균 → argmax = `action_label`, 그 값 = `confidence` |
| 짧은 영상 | `_predict_track()` `whole_track` | Window 가 한 번도 안 차면 보인 구간 전체를 30 Step 으로 한 번 예측 (유효 프레임 10개 이상) |
| 예측 없음 | | 유효 프레임 10개 미만 → 그 사람은 결과에서 빠짐 · `message` 로 이유 안내 |

FastAPI 는 무거운 `process_video` · `predict_tracks` 를 `run_in_threadpool` 로 돌려 이벤트 루프를 막지 않습니다.

## 4. 처리 시간 (B8)

같은 `wave.mp4` (640×480 · 25fps · 126 frames · 5.04초 · 1명) 6회, 첫 회 워밍업 제외, CPU i7-12700 · GPU 없음

| 지표 | p50 | 범위 |
|---|---|---|
| AI 추론 `processing_ms` | **3,331 ms** | 3,295 ~ 3,345 (±0.8%) |
| 접수 → 완료 | 3.349 초 | 3.323 ~ 3.366 |
| 접수 → Worker 시작 | 0.013 초 | 0.012 ~ 0.020 |

- 전체 시간의 **99.3% 가 AI 추론**입니다. 웹 · 큐 · 저장은 18 ~ 28 ms.
- 첫 요청은 +39% (4,645 ms) · 서버 재시작 뒤 YOLO 첫 실행 비용.
- 1명 · 5초 한 조건만 측정했습니다. 2명 · 30프레임 영상(job 9)은 1,901 ms.

## 5. 결과 재현성

같은 영상을 4번 넣었을 때 `wave` · confidence **0.4533** 이 매번 같았습니다 (B5 · DB 직접 조회). 모델과 Feature 계산이 결정적이라는 뜻이고, 낮은 값은 모델 자체의 한계입니다.

## 6. 데이터 한계

| 사실 | 근거 |
|---|---|
| 학습 데이터는 **한 사람(S01) · 동작당 1개 · 클립 6개** | `rf_training_info.json` `train_clips 6` · `subjects ["S01"]` |
| 학습에 없던 사람(S02)의 손 흔들기 → `drink_return` 0.22 (무작위 0.167 과 비슷) | 웹 결과 · 학습 프로젝트 검증 결과에 같은 값이 기록돼 있음 → 웹 코드 문제가 아님 |
| 3초 Window 로 다시 돌려도 UNKNOWN 0.29 | 학습 프로젝트 기록 |
| IP Webcam 손 흔들기는 `sit_stand` 로 자주 나옴 · 해상도 · 방향 · Pose conf 를 바꿔도 해결 안 됨 | [evidence/logs/webcam_retry_compare.txt](evidence/logs/webcam_retry_compare.txt) |

그래서 이 저장소에서는 모델을 바꾸지 않고 다음으로 대응했습니다.

- Label 과 Confidence 를 함께 보여 주고, 0.55 미만은 **「판단 불확실」** 로 표시 (`is_uncertain`)
- 6개 확률을 모두 저장해 나중에 비교할 수 있게 함
- 화면 안내: 「예측 결과는 참고용이며 정답이나 위험행동 판정이 아닙니다」

다음 단계는 여러 사람 데이터로 다시 학습한 뒤 `ai_service/models/` 의 파일만 바꾸는 것입니다. 열 순서 · Class 검사가 있어 잘못된 모델은 시작 단계에서 막힙니다.
