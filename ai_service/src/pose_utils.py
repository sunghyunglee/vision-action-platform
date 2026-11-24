from __future__ import annotations


# ① COCO 17개 Keypoint의 이름 정의
# YOLO Pose가 검출한 관절 번호(0~16)에 해당하는 이름
COCO_KEYPOINT_NAMES = [
    "nose",            # 0: 코
    "left_eye",        # 1: 왼쪽 눈
    "right_eye",       # 2: 오른쪽 눈
    "left_ear",        # 3: 왼쪽 귀
    "right_ear",       # 4: 오른쪽 귀
    "left_shoulder",   # 5: 왼쪽 어깨
    "right_shoulder",  # 6: 오른쪽 어깨
    "left_elbow",      # 7: 왼쪽 팔꿈치
    "right_elbow",     # 8: 오른쪽 팔꿈치
    "left_wrist",      # 9: 왼쪽 손목
    "right_wrist",     # 10: 오른쪽 손목
    "left_hip",       # 11: 왼쪽 골반
    "right_hip",      # 12: 오른쪽 골반
    "left_knee",      # 13: 왼쪽 무릎
    "right_knee",     # 14: 오른쪽 무릎
    "left_ankle",     # 15: 왼쪽 발목
    "right_ankle",    # 16: 오른쪽 발목
]
