from pathlib import Path
import cv2
import mediapipe as mp


class HandTracker:
    CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (0, 9), (9, 10), (10, 11), (11, 12),
        (0, 13), (13, 14), (14, 15), (15, 16),
        (0, 17), (17, 18), (18, 19), (19, 20),
        (5, 9), (9, 13), (13, 17),
    ]

    def __init__(
        self,
        model_path: str,
        num_hands: int = 1,
        detection_confidence: float = 0.5,
        presence_confidence: float = 0.5,
        tracking_confidence: float = 0.5,
    ):
        base_options = mp.tasks.BaseOptions(
            model_asset_path=str(Path(model_path).resolve())
        )

        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=detection_confidence,
            min_hand_presence_confidence=presence_confidence,
            min_tracking_confidence=tracking_confidence,
        )

        self.detector = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self.timestamp_ms = 0

    def process(self, frame_bgr):
        if frame_bgr is None:
            return {"hands": [], "result": None}

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb,
        )

        self.timestamp_ms += 1

        result = self.detector.detect_for_video(
            mp_image,
            self.timestamp_ms,
        )

        return {
            "hands": result.hand_landmarks,
            "handedness": result.handedness,
            "result": result,
        }

    @staticmethod
    def landmarks_to_pixels(landmarks, frame_shape):
        h, w = frame_shape[:2]
        points = []
        for lm in landmarks:
            x = int(max(0.0, min(1.0, lm.x)) * w)
            y = int(max(0.0, min(1.0, lm.y)) * h)
            points.append((x, y))
        return points

    def draw(self, frame, detection_data):
        if not detection_data:
            return frame

        hands = detection_data.get("hands", [])

        for landmarks in hands:
            points = self.landmarks_to_pixels(landmarks, frame.shape)

            for x, y in points:
                cv2.circle(
                    frame, (x, y), 4, (0, 220, 255), -1, cv2.LINE_AA
                )

            for start, end in self.CONNECTIONS:
                cv2.line(
                    frame,
                    points[start],
                    points[end],
                    (50, 255, 50),
                    2,
                    cv2.LINE_AA,
                )

        return frame

    def close(self):
        self.detector.close()
