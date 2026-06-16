import os
import cv2
import base64
from pathlib import Path
from typing import Any, List, Dict, Tuple
import yaml
from backend_logs import backend_logs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LATEST_RUN_DIR = PROJECT_ROOT / "latest_run"
CONFIG_PATH = LATEST_RUN_DIR / "config" / "default.yaml"
DEFAULT_MODEL_PATH = LATEST_RUN_DIR / "outputs" / "best.pt"
DEFAULT_CLASS_NAMES = ["motor", "auto", "car", "heavy"]


def _load_latest_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_local_path(path_value: str | os.PathLike | None) -> Path | None:
    if not path_value:
        return None

    path = Path(path_value)
    candidates = [path] if path.is_absolute() else [PROJECT_ROOT / path, LATEST_RUN_DIR / path]

    # The notebook writes Colab paths like project/outputs/best.pt. Locally,
    # latest_run is the exported project folder.
    if not path.is_absolute() and path.parts and path.parts[0] == "project":
        candidates.append(LATEST_RUN_DIR.joinpath(*path.parts[1:]))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1] if candidates else None


def _resolve_model_path(config: Dict[str, Any]) -> Path:
    configured_path = config.get("inference", {}).get("model_path")
    for path_value in [os.getenv("TRAFFICAI_MODEL_PATH"), configured_path, DEFAULT_MODEL_PATH, PROJECT_ROOT / "best.pt"]:
        path = _resolve_local_path(path_value)
        if path and path.exists():
            return path
    raise FileNotFoundError(
        f"No YOLO model found. Expected latest model at {DEFAULT_MODEL_PATH} "
        "or set TRAFFICAI_MODEL_PATH."
    )


def _resolve_device(config: Dict[str, Any]) -> str | int:
    configured_device = config.get("inference", {}).get("device", "cpu")
    if str(configured_device).lower() == "cpu":
        return "cpu"

    try:
        import torch
        if torch.cuda.is_available():
            return configured_device
    except Exception:
        pass
    return "cpu"


def _get_class_names(config: Dict[str, Any]) -> List[str]:
    names = config.get("dataset", {}).get("names")
    if isinstance(names, list) and names:
        return [str(name) for name in names]
    return DEFAULT_CLASS_NAMES.copy()

class InferenceEngine:
    """Handles YOLOv8 inference on images."""
    def __init__(self):
        self.config = _load_latest_config()
        inference_config = self.config.get("inference", {})
        self.model_path = _resolve_model_path(self.config)
        self.conf_threshold = float(inference_config.get("conf_threshold", 0.25))
        self.iou_threshold = float(inference_config.get("iou_threshold", 0.45))
        self.class_names = _get_class_names(self.config)
        self.device = _resolve_device(self.config)

        # Lazy import to avoid loading on module import
        from ultralytics import YOLO
        print(f"[InferenceEngine] Loading model from: {self.model_path}")
        backend_logs.add(
            "INFO",
            "InferenceEngine",
            "Loading YOLO model",
            details={"model_path": str(self.model_path), "device": str(self.device)},
        )
        print(f"[InferenceEngine] Classes: {', '.join(self.class_names)}")
        self.model = YOLO(str(self.model_path))
        print(f"[InferenceEngine] Model loaded on {self.device}")
        backend_logs.add(
            "INFO",
            "InferenceEngine",
            "YOLO model loaded",
            details={"classes": self.class_names, "device": str(self.device)},
        )

    def run_inference(self, image) -> List[Dict]:
        """Run YOLO inference on an image path or OpenCV image."""
        if isinstance(image, (str, Path)):
            image_path = str(image)
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")
        elif image is None:
            raise ValueError("Could not run inference on an empty image")

        results = self.model(
            image,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
        )[0]

        detections = []
        if results.boxes is not None:
            for *xyxy, conf, cls in results.boxes.data.tolist():
                class_id = int(cls)
                if class_id < len(self.class_names):
                    detections.append({
                        "bbox": [int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])],
                        "confidence": float(conf),
                        "class_id": class_id,
                        "class_name": self.class_names[class_id],
                    })
        return detections

    def annotate_image(self, image_path: str, detections: List[Dict]) -> str:
        """Draw bounding boxes on image and return base64 encoded string."""
        image = cv2.imread(image_path)
        if image is None:
            return None

        colors = {
            "motor": (0, 255, 0),
            "auto": (0, 165, 255),
            "car": (255, 0, 0),
            "heavy": (0, 0, 255),
        }

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            class_name = det["class_name"]
            conf = det["confidence"]
            color = colors.get(class_name, (0, 255, 0))
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            label = f"{class_name} {conf:.2f}"
            cv2.putText(image, label, (x1, max(20, y1 - 8)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Encode to base64
        _, buffer = cv2.imencode(".jpg", image)
        img_str = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"


class DensityCalculator:
    """Calculates traffic density and green light duration."""
    MAX_CAPACITY = 100
    WEIGHTS = {
        "motor": 1,
        "auto": 2,
        "car": 3,
        "heavy": 5,
    }

    def __init__(self, class_names: List[str] | None = None):
        self.class_names = class_names or DEFAULT_CLASS_NAMES.copy()

    def empty_counts(self) -> Dict[str, int]:
        return {class_name: 0 for class_name in self.class_names}

    def calculate(self, detections: List[Dict]) -> Tuple[float, Dict[str, int]]:
        """
        Returns:
            density: float (percentage 0-100+)
            vehicle_counts: Dict[class_name, count]
        """
        counts = self.empty_counts()
        for det in detections:
            class_name = det["class_name"]
            counts[class_name] = counts.get(class_name, 0) + 1

        weighted_count = sum(
            count * self.WEIGHTS.get(class_name, 1)
            for class_name, count in counts.items()
        )

        density = (weighted_count / self.MAX_CAPACITY) * 100
        return density, counts

    def calculate_green_time(self, density: float, max_green_time: int) -> int:
        """Calculate green light duration based on density."""
        duration = int((density / 100) * max_green_time)
        return max(5, min(duration, max_green_time))  # Min 5s, max max_green_time


class AnalysisEngine:
    """Combines inference and density calculation."""
    def __init__(self):
        self.inference = InferenceEngine()
        self.density = DensityCalculator(self.inference.class_names)

    def analyze_image(self, image_path: str, max_green_time: int) -> Dict:
        """Analyze a single image and return complete lane data."""
        detections = self.inference.run_inference(image_path)
        density_value, counts = self.density.calculate(detections)
        annotated_image = self.inference.annotate_image(image_path, detections)
        green_time = self.density.calculate_green_time(density_value, max_green_time)

        backend_logs.add(
            "INFO",
            "InferenceEngine",
            "Image analyzed",
            details={
                "image_path": image_path,
                "detections": len(detections),
                "density": round(density_value, 1),
                "green_time": green_time,
                "vehicle_counts": counts,
            },
        )

        return {
            "image_url": annotated_image,
            "density": round(density_value, 1),
            "vehicle_counts": counts,
            "green_time": green_time,
            "detections": detections,
        }
