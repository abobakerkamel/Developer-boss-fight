from pathlib import Path
from urllib.request import urlopen


MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)


def ensure_hand_landmarker_model(model_path: Path) -> Path:
    model_path = Path(model_path)

    if model_path.exists() and model_path.stat().st_size > 0:
        return model_path

    model_path.parent.mkdir(parents=True, exist_ok=True)

    print("MediaPipe model not found.")
    print("Downloading official Hand Landmarker model...")

    with urlopen(MODEL_URL, timeout=60) as response:
        data = response.read()

    model_path.write_bytes(data)

    print(f"Model saved to: {model_path}")
    return model_path
