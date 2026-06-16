from ultralytics import YOLO

class InferenceEngine:
    def __init__(self, config):
        self.config = config
        self.model_path = config['inference']['model_path']
        self.conf_threshold = config['inference']['conf_threshold']
        self.iou_threshold = config['inference']['iou_threshold']
        self.device = config['inference']['device']
        self.class_names = config['dataset'].get('names', ['motor', 'auto', 'car', 'heavy'])
        print(f"Loading YOLO model from: {self.model_path}")
        self.model = YOLO(self.model_path)

    def run_inference(self, image):
        results = self.model(image, conf=self.conf_threshold, iou=self.iou_threshold, device=self.device, verbose=False)[0]
        detections = []
        if results.boxes is not None:
            for *xyxy, conf, cls in results.boxes.data.tolist():
                class_id = int(cls)
                if class_id < len(self.class_names):
                    detections.append([int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3]), float(conf), class_id, self.class_names[class_id]])
        return detections
