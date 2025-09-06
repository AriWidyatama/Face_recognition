import numpy as np
from collections import deque

LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]

def eye_aspect_ratio(landmarks, eye_idx, img_shape):
    h, w = img_shape[:2]
    pts = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in eye_idx]
    A = np.linalg.norm(np.array(pts[1]) - np.array(pts[5]))
    B = np.linalg.norm(np.array(pts[2]) - np.array(pts[4]))
    C = np.linalg.norm(np.array(pts[0]) - np.array(pts[3]))
    ear = (A + B) / (2.0 * C)
    return ear

class BlinkLiveness:
    def __init__(self, ear_threshold=0.21, consec_frames=2, window_size=30, min_blinks=1):
        self.ear_threshold = ear_threshold
        self.consec_frames = consec_frames
        self.window_size = window_size
        self.min_blinks = min_blinks
        self.blink_counters = {}
        self.blink_history = {}

    def update(self, face_id, landmarks, frame_shape):
        left_ear = eye_aspect_ratio(landmarks, LEFT_EYE_IDX, frame_shape)
        right_ear = eye_aspect_ratio(landmarks, RIGHT_EYE_IDX, frame_shape)
        ear = (left_ear + right_ear) / 2.0

        if face_id not in self.blink_counters:
            self.blink_counters[face_id] = 0
            self.blink_history[face_id] = deque(maxlen=self.window_size)

        if ear < self.ear_threshold:
            self.blink_counters[face_id] += 1
        else:
            if self.blink_counters[face_id] >= self.consec_frames:
                self.blink_history[face_id].append(1)
            else:
                self.blink_history[face_id].append(0)
            self.blink_counters[face_id] = 0

        live = sum(self.blink_history[face_id]) >= self.min_blinks
        return live