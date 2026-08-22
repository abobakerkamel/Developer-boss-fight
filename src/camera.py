import cv2


class Camera:
    def __init__(self, camera_index=0, width=1280, height=720, fps=30):
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(camera_index)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"Cannot open camera with index {camera_index}"
            )

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

    def read(self):
        success, frame = self.cap.read()
        if not success:
            return None
        return cv2.flip(frame, 1)

    def release(self):
        if self.cap is not None:
            self.cap.release()
