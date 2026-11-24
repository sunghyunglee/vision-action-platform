from __future__ import annotations

import numpy as np

from src.feature_utils import (
    normalize_by_shoulder_width,
    selected_joint_angles,
)


def feature_from_keypoints(keypoints):
    keypoints = np.asarray(
        keypoints,
        dtype=np.float32,
    )

    if keypoints.shape != (17, 2):
        return None

    if not np.all(np.isfinite(keypoints)):
        return None

    try:
        normalized, _, _ = (
            normalize_by_shoulder_width(keypoints)
        )
    except ValueError:
        return None

    angles = selected_joint_angles(keypoints)

    feature = []

    for point in normalized:
        feature.extend(
            [
                float(point[0]),
                float(point[1]),
            ]
        )

    feature.extend(
        [
            float(angles["left_elbow_angle"]),
            float(angles["right_elbow_angle"]),
            float(angles["left_knee_angle"]),
            float(angles["right_knee_angle"]),
        ]
    )

    feature = np.asarray(
        feature,
        dtype=np.float32,
    )

    if len(feature) != 38:
        return None

    if not np.all(np.isfinite(feature)):
        return None

    return feature
    