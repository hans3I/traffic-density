import cv2
import numpy as np

class VisualizationEngine:
    def __init__(self, config):
        self.config = config
        self.colors = {
            'motor': (0, 255, 0),
            'auto': (0, 165, 255),
            'car': (255, 0, 0),
            'heavy': (0, 0, 255),
            'North': (255, 255, 0),
            'East': (0, 255, 255),
            'South': (255, 0, 255),
            'West': (128, 0, 128),
            'Unassigned': (200, 200, 200),
        }

    def draw_detections(self, image, detections, roi_counts):
        annotated = image.copy()
        for direction, points in self.config['roi_counting']['roi_polygons'].items():
            if points and len(points) >= 3:
                polygon_np = np.array(points, np.int32)
                color = self.colors.get(direction, (255, 255, 255))
                cv2.polylines(annotated, [polygon_np], True, color, 2)
                cv2.putText(annotated, direction, tuple(polygon_np[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            class_name = detection['class_name']
            confidence = detection['confidence']
            direction = detection.get('roi_direction') or 'Unassigned'
            color = self.colors.get(class_name, (0, 255, 0))
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated, f"{class_name} {confidence:.2f} {direction}", (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        y = 30
        for direction in ['North', 'East', 'South', 'West']:
            cv2.putText(annotated, f"{direction}: {roi_counts.get(direction, 0)}", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y += 25
        return annotated
