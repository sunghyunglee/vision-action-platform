from __future__ import annotations

import numpy as np

from src.pose_utils import (
    COCO_KEYPOINT_NAMES,
)


FRAME_FEATURE_NAMES = []

for name in COCO_KEYPOINT_NAMES:
    FRAME_FEATURE_NAMES.extend(
        [
            f"{name}_x",
            f"{name}_y",
        ]
    )

FRAME_FEATURE_NAMES.extend(
    [
        "left_elbow_angle",
        "right_elbow_angle",
        "left_knee_angle",
        "right_knee_angle",
    ]
)


def resample_sequence(
    frame_features,
    frame_ids,
    target_steps: int = 30,
):
    frame_features = np.asarray(
        frame_features,
        dtype=np.float32,
    )

    frame_ids = np.asarray(
        frame_ids,
        dtype=np.float32,
    )

    if frame_features.ndim != 2:
        raise ValueError(
            "frame_features는 "
            "(T, F) 형태여야 합니다."
        )

    if len(frame_features) != len(
        frame_ids
    ):
        raise ValueError(
            "Feature 수와 Frame ID 수가 "
            "다릅니다."
        )

    if len(frame_features) < 2:
        raise ValueError(
            "유효한 Frame Feature가 "
            "2개 이상 필요합니다."
        )

    if target_steps < 2:
        raise ValueError(
            "target_steps는 "
            "2 이상이어야 합니다."
        )

    span = (
        frame_ids[-1]
        - frame_ids[0]
    )

    if span <= 0:
        raise ValueError(
            "Frame 시간 순서를 "
            "확인할 수 없습니다."
        )

    original_x = (
        frame_ids
        - frame_ids[0]
    ) / span

    target_x = np.linspace(
        0.0,
        1.0,
        target_steps,
    )

    output = np.empty(
        (
            target_steps,
            frame_features.shape[1],
        ),
        dtype=np.float32,
    )

    for feature_index in range(
        frame_features.shape[1]
    ):
        output[
            :,
            feature_index,
        ] = np.interp(
            target_x,
            original_x,
            frame_features[
                :,
                feature_index,
            ],
        )

    return output


def flatten_sequence(
    sequence,
):
    return np.asarray(
        sequence,
        dtype=np.float32,
    ).reshape(-1)


def sequence_feature_names(
    target_steps: int,
):
    names = []

    for step in range(
        target_steps
    ):
        for feature_name in (
            FRAME_FEATURE_NAMES
        ):
            names.append(
                f"t{step:02d}_"
                f"{feature_name}"
            )

    return names


    