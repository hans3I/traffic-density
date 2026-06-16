import cv2
import numpy as np

class ROIEngine:
    def __init__(self, config):
        self.config = config
        self.roi_polygons = config['roi_counting']['roi_polygons']

    def assign_detection_to_roi(self, detection, image_width, image_height):
        x1, y1, x2, y2 = detection[:4]
        center = ((x1 + x2) / 2, (y1 + y2) / 2)
        # First-match assignment is intentional if manually edited ROIs overlap later.
        for direction, polygon_points in self.roi_polygons.items():
            if polygon_points and len(polygon_points) >= 3:
                polygon_np = np.array(polygon_points, np.int32)
                if cv2.pointPolygonTest(polygon_np, center, False) >= 0:
                    return direction
        return None

    def count_vehicles_in_rois(self, detections, image_width, image_height):
        counts = {direction: 0 for direction in self.roi_polygons.keys()}
        assigned = {direction: [] for direction in self.roi_polygons.keys()}
        unassigned = []
        for detection in detections:
            direction = self.assign_detection_to_roi(detection, image_width, image_height)
            if direction:
                counts[direction] += 1
                assigned[direction].append(detection)
            else:
                unassigned.append(detection)
        return counts, assigned, unassigned
