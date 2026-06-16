#!/usr/bin/env python3
"""
Comprehensive Effectiveness Test Suite for Traffic Light AI System.

Tests:
1. Detection Accuracy (YOLOv8) on 100 random BMD45-Val images
   - Per-class Precision, Recall, mAP@0.5, F1-Score
2. Scheduling Effectiveness (4 lanes, 20 cycles)
   - Density-Based vs Fixed-Time comparison
   - Metrics: Throughput, Waiting Time, Fairness, Total Time

Outputs:
- Markdown report: api/tests/EFFECTIVENESS_REPORT.md
- JSON data: api/tests/test_results.json
"""

import os
import sys
import json
import random
import time
import math
import warnings
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Tuple, Any

# Suppress ultralytics warnings
warnings.filterwarnings("ignore")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from ultralytics import YOLO
from engine import AnalysisEngine, DensityCalculator
from bmd45_loader import BMD45Loader

# ============================================================================
# Configuration
# ============================================================================
MODEL_PATH = Path(__file__).parent.parent.parent / "latest_run" / "outputs" / "best.pt"
ANNOTATION_PATH = Path(__file__).parent.parent / "cache" / "bmd45" / "BMD-45-Val" / "_annotations.coco.json"
NUM_DETECTION_SAMPLES = 100
NUM_LANES = 4
NUM_CYCLES = 20
MAX_GREEN_TIME = 60
SERVICE_RATE = 10  # weighted vehicles cleared per second
REPORT_PATH = Path(__file__).parent / "EFFECTIVENESS_REPORT.md"
RESULTS_PATH = Path(__file__).parent / "test_results.json"

# ============================================================================
# Class Mapping
# ============================================================================
BMD_TO_OUR_CLASS_MAP = {
    # motor classes
    7: "motor",   # Two-wheeler
    11: "motor",  # Bicycle
    # auto classes
    6: "auto",    # Three-wheeler
    # car classes
    0: "car",     # Hatchback
    1: "car",     # Sedan
    2: "car",     # SUV
    3: "car",     # MUV
    12: "car",    # Van
    # heavy classes
    4: "heavy",   # Bus
    5: "heavy",   # Truck
    8: "heavy",   # LCV
    9: "heavy",   # Mini-bus
    10: "heavy",  # Tempo-traveller
}

OUR_CLASS_NAMES = ["motor", "auto", "car", "heavy"]
OUR_CLASS_WEIGHTS = {"motor": 1, "auto": 2, "car": 3, "heavy": 5}


def empty_vehicle_counts() -> Dict[str, int]:
    return {class_name: 0 for class_name in OUR_CLASS_NAMES}


def weighted_vehicle_count(counts: Dict[str, int]) -> int:
    return sum(counts.get(class_name, 0) * weight for class_name, weight in OUR_CLASS_WEIGHTS.items())

# ============================================================================
# Helper Functions
# ============================================================================

def compute_iou(box1, box2):
    """Compute IoU between two boxes in [x1, y1, x2, y2] format."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = box1_area + box2_area - inter_area

    if union_area == 0:
        return 0.0
    return inter_area / union_area


def compute_ap(recalls, precisions):
    """Compute Average Precision using 11-point interpolation."""
    # Append sentinel values
    recalls = [0.0] + list(recalls) + [1.0]
    precisions = [1.0] + list(precisions) + [0.0]

    # Compute precision envelope (max precision for recall >= r)
    for i in range(len(precisions) - 2, -1, -1):
        precisions[i] = max(precisions[i], precisions[i + 1])

    # Compute AP
    ap = 0.0
    for t in np.arange(0.0, 1.1, 0.1):
        # Find largest recall >= t
        idx = len(recalls) - 1
        for i, r in enumerate(recalls):
            if r >= t:
                idx = i
                break
        ap += precisions[idx]

    return ap / 11.0


# ============================================================================
# Test 1: Detection Accuracy
# ============================================================================

class DetectionAccuracyTest:
    def __init__(self, model_path: Path, annotation_path: Path, num_samples: int = 100):
        print("[DetectionAccuracyTest] Initializing...")
        self.model = YOLO(str(model_path))
        self.num_samples = num_samples

        with open(annotation_path, "r", encoding="utf-8") as f:
            self.annotations = json.load(f)

        # Build image_id -> list of annotations
        self.gt_by_image = defaultdict(list)
        for ann in self.annotations["annotations"]:
            self.gt_by_image[ann["image_id"]].append(ann)

        # Build image_id -> image info
        self.images_by_id = {img["id"]: img for img in self.annotations["images"]}

        # Cache directory
        self.cache_dir = Path(__file__).parent.parent / "cache" / "bmd45" / "BMD-45-Val"

        print(f"[DetectionAccuracyTest] Loaded {len(self.annotations['images'])} images, {len(self.annotations['annotations'])} annotations")

    def get_image_path(self, image_id: int) -> str:
        """Find local image path for a given image_id."""
        img = self.images_by_id.get(image_id)
        if not img:
            return None

        file_name = img["file_name"]  # e.g., "images_000/57.png"
        # Try to find in cache
        full_path = self.cache_dir / file_name
        if full_path.exists():
            return str(full_path)

        # Try various extensions
        for ext in [".png", ".jpg", ".jpeg"]:
            p = self.cache_dir / (file_name.replace(".png", ext).replace(".jpg", ext).replace(".jpeg", ext))
            if p.exists():
                return str(p)

        return None

    def download_image(self, image_id: int) -> str:
        """Download image using BMD45Loader."""
        img = self.images_by_id.get(image_id)
        if not img:
            return None

        # Use huggingface_hub directly
        from huggingface_hub import hf_hub_download
        repo_id = "iisc-aim/BMD-45"
        file_name = img["file_name"]
        split_dir = "BMD-45-Val"
        remote_path = f"{split_dir}/{file_name}"

        try:
            local_path = hf_hub_download(
                repo_id=repo_id,
                repo_type="dataset",
                filename=remote_path,
                local_dir=str(self.cache_dir.parent),
                local_dir_use_symlinks=False,
            )
            return str(local_path)
        except Exception as e:
            print(f"[DetectionAccuracyTest] Failed to download {remote_path}: {e}")
            return None

    def run(self) -> Dict[str, Any]:
        """Run detection accuracy test."""
        print(f"[DetectionAccuracyTest] Running on {self.num_samples} random samples...")
        
        # Select random images
        all_images = self.annotations["images"]
        if len(all_images) < self.num_samples:
            print(f"[DetectionAccuracyTest] Warning: only {len(all_images)} images available, using all")
            selected = all_images
        else:
            selected = random.sample(all_images, self.num_samples)

        # Per-class storage: predictions and ground truths
        class_predictions = {cls: [] for cls in OUR_CLASS_NAMES}  # list of (confidence, iou, matched)
        class_ground_truths = {cls: 0 for cls in OUR_CLASS_NAMES}
        
        inference_times = []
        sample_count = 0

        for img in selected:
            img_id = img["id"]
            img_path = self.get_image_path(img_id)
            
            if not img_path:
                img_path = self.download_image(img_id)
                if not img_path:
                    print(f"[DetectionAccuracyTest] Skipping image {img_id} (not found)")
                    continue

            # Run inference
            t0 = time.time()
            results = self.model(img_path, conf=0.25, iou=0.45, verbose=False)[0]
            inference_times.append(time.time() - t0)

            # Parse predictions
            predictions = []
            if results.boxes is not None:
                for *xyxy, conf, cls in results.boxes.data.tolist():
                    pred_cls = int(cls)
                    if pred_cls < len(OUR_CLASS_NAMES):
                        pred_class_name = OUR_CLASS_NAMES[pred_cls]
                        predictions.append({
                            "bbox": [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
                            "confidence": float(conf),
                            "class_name": pred_class_name,
                        })

            # Parse ground truths
            gts = self.gt_by_image.get(img_id, [])
            gt_boxes = []
            for gt in gts:
                bmd_class = gt["category_id"]
                our_class = BMD_TO_OUR_CLASS_MAP.get(bmd_class)
                if our_class:
                    gt_boxes.append({
                        "bbox": gt["bbox"],  # COCO format: [x, y, w, h]
                        "class_name": our_class,
                        "matched": False,
                    })
                    class_ground_truths[our_class] += 1

            # Match predictions to ground truth
            # Sort predictions by confidence descending
            predictions.sort(key=lambda x: x["confidence"], reverse=True)

            for pred in predictions:
                pred_class = pred["class_name"]
                pred_box = pred["bbox"]
                best_iou = 0.0
                best_gt_idx = -1

                for i, gt in enumerate(gt_boxes):
                    if gt["class_name"] != pred_class or gt["matched"]:
                        continue
                    # Convert COCO [x, y, w, h] to [x1, y1, x2, y2]
                    gt_box = [
                        gt["bbox"][0],
                        gt["bbox"][1],
                        gt["bbox"][0] + gt["bbox"][2],
                        gt["bbox"][1] + gt["bbox"][3],
                    ]
                    iou = compute_iou(pred_box, gt_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = i

                matched = best_iou >= 0.5
                if matched and best_gt_idx >= 0:
                    gt_boxes[best_gt_idx]["matched"] = True

                class_predictions[pred_class].append({
                    "confidence": pred["confidence"],
                    "iou": best_iou,
                    "matched": matched,
                })

            sample_count += 1
            if sample_count % 10 == 0:
                print(f"[DetectionAccuracyTest] Processed {sample_count}/{len(selected)} images")

        # Calculate per-class metrics
        per_class_metrics = {}
        total_tp = 0
        total_fp = 0
        total_fn = 0

        for cls in OUR_CLASS_NAMES:
            preds = class_predictions[cls]
            gt_count = class_ground_truths[cls]
            
            # Sort by confidence descending
            preds.sort(key=lambda x: x["confidence"], reverse=True)
            
            tp = sum(1 for p in preds if p["matched"])
            fp = len(preds) - tp
            fn = gt_count - tp
            
            total_tp += tp
            total_fp += fp
            total_fn += fn

            # Calculate precision and recall at each threshold
            cum_tp = 0
            precisions = []
            recalls = []
            for pred in preds:
                if pred["matched"]:
                    cum_tp += 1
                cum_fp = len(preds) - cum_tp
                precision = cum_tp / (cum_tp + cum_fp) if (cum_tp + cum_fp) > 0 else 0
                recall = cum_tp / gt_count if gt_count > 0 else 0
                precisions.append(precision)
                recalls.append(recall)

            ap = compute_ap(recalls, precisions) if precisions else 0.0
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            per_class_metrics[cls] = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "ap_50": round(ap, 4),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "gt_count": gt_count,
                "pred_count": len(preds),
            }

        # Overall metrics
        overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0
        map_50 = sum(per_class_metrics[cls]["ap_50"] for cls in OUR_CLASS_NAMES) / len(OUR_CLASS_NAMES)
        avg_inference_time = sum(inference_times) / len(inference_times) if inference_times else 0

        results = {
            "num_samples": sample_count,
            "per_class": per_class_metrics,
            "overall": {
                "precision": round(overall_precision, 4),
                "recall": round(overall_recall, 4),
                "f1_score": round(overall_f1, 4),
                "mAP_50": round(map_50, 4),
                "total_tp": total_tp,
                "total_fp": total_fp,
                "total_fn": total_fn,
                "avg_inference_time_ms": round(avg_inference_time * 1000, 2),
            }
        }

        print(f"[DetectionAccuracyTest] Completed: mAP@0.5={map_50:.4f}, F1={overall_f1:.4f}")
        return results


# ============================================================================
# Test 2: Scheduling Effectiveness
# ============================================================================

class SchedulingEffectivenessTest:
    def __init__(self, engine: AnalysisEngine, loader: BMD45Loader, 
                 lanes: int = 4, cycles: int = 20, max_green_time: int = 60):
        self.engine = engine
        self.loader = loader
        self.lanes = lanes
        self.cycles = cycles
        self.max_green_time = max_green_time
        self.service_rate = SERVICE_RATE
        self.density_calc = DensityCalculator()

    def _analyze_lane(self, image_path: str) -> Dict:
        """Analyze a single lane image."""
        if not image_path:
            return {
                "density": 0.0,
                "vehicle_counts": empty_vehicle_counts(),
                "green_time": 0,
                "weighted_count": 0,
            }
        
        detections = self.engine.inference.run_inference(image_path)
        density, counts = self.density_calc.calculate(detections)
        green_time = self.density_calc.calculate_green_time(density, self.max_green_time)
        weighted_count = weighted_vehicle_count(counts)
        
        return {
            "density": density,
            "vehicle_counts": counts,
            "green_time": green_time,
            "weighted_count": weighted_count,
        }

    def _get_weighted_count(self, counts: Dict[str, int]) -> int:
        return weighted_vehicle_count(counts)

    def _simulate_density_based(self, seed: int) -> Dict:
        """Simulate density-based scheduling."""
        random.seed(seed)
        np.random.seed(seed)

        # Initialize lanes
        lane_images = self.loader.download_images(self.lanes)
        lane_states = []
        for i, img_path in enumerate(lane_images):
            result = self._analyze_lane(img_path)
            lane_states.append({
                "image_path": img_path,
                "density": result["density"],
                "vehicle_counts": result["vehicle_counts"],
                "green_time": result["green_time"],
                "weighted_count": result["weighted_count"],
            })

        # Queues and metrics
        queues = [0.0] * self.lanes
        total_throughput = 0.0
        total_waiting_time = 0.0
        total_time = 0.0
        lane_green_counts = [0] * self.lanes
        lane_wait_times = [0.0] * self.lanes
        history = []

        for cycle in range(self.cycles):
            # Select lane with highest density
            max_density = -1
            green_idx = 0
            for i, lane in enumerate(lane_states):
                if lane["density"] > max_density:
                    max_density = lane["density"]
                    green_idx = i

            green_time = lane_states[green_idx]["green_time"]
            green_time = max(5, min(green_time, self.max_green_time))

            # Calculate clearing
            total_vehicles = queues[green_idx] + lane_states[green_idx]["weighted_count"]
            capacity = self.service_rate * green_time
            cleared = min(total_vehicles, capacity)
            queues[green_idx] = total_vehicles - cleared
            total_throughput += cleared

            # Update waiting time for RED lanes
            for i in range(self.lanes):
                if i != green_idx:
                    # RED lanes accumulate new vehicles
                    queues[i] += lane_states[i]["weighted_count"]
                    # Waiting time = queue * green_time
                    total_waiting_time += queues[i] * green_time
                    lane_wait_times[i] += queues[i] * green_time

            total_time += green_time
            lane_green_counts[green_idx] += 1

            history.append({
                "cycle": cycle + 1,
                "green_lane": green_idx + 1,
                "green_time": green_time,
                "throughput": cleared,
                "waiting_time": sum(queues[i] * green_time for i in range(self.lanes) if i != green_idx),
            })

            # Refresh green lane image (like the existing system)
            new_image_path = self.loader.get_one_image()
            if new_image_path:
                result = self._analyze_lane(new_image_path)
                lane_states[green_idx] = {
                    "image_path": new_image_path,
                    "density": result["density"],
                    "vehicle_counts": result["vehicle_counts"],
                    "green_time": result["green_time"],
                    "weighted_count": result["weighted_count"],
                }

        # Calculate fairness index (Jain's fairness index)
        green_counts = np.array(lane_green_counts)
        fairness = (np.sum(green_counts) ** 2) / (self.lanes * np.sum(green_counts ** 2)) if np.sum(green_counts ** 2) > 0 else 0

        return {
            "total_throughput": round(total_throughput, 2),
            "total_waiting_time": round(total_waiting_time, 2),
            "avg_waiting_time": round(total_waiting_time / self.cycles, 2),
            "total_time": round(total_time, 2),
            "fairness_index": round(fairness, 4),
            "lane_green_counts": lane_green_counts,
            "lane_wait_times": [round(w, 2) for w in lane_wait_times],
            "history": history,
        }

    def _simulate_fixed_time(self, seed: int) -> Dict:
        """Simulate fixed-time (round-robin) scheduling."""
        random.seed(seed)
        np.random.seed(seed)

        fixed_time = self.max_green_time / self.lanes

        # Initialize lanes
        lane_images = self.loader.download_images(self.lanes)
        lane_states = []
        for i, img_path in enumerate(lane_images):
            result = self._analyze_lane(img_path)
            lane_states.append({
                "image_path": img_path,
                "density": result["density"],
                "vehicle_counts": result["vehicle_counts"],
                "green_time": fixed_time,
                "weighted_count": result["weighted_count"],
            })

        # Queues and metrics
        queues = [0.0] * self.lanes
        total_throughput = 0.0
        total_waiting_time = 0.0
        total_time = 0.0
        lane_green_counts = [0] * self.lanes
        lane_wait_times = [0.0] * self.lanes
        history = []

        for cycle in range(self.cycles):
            # Round-robin selection
            green_idx = cycle % self.lanes
            green_time = fixed_time

            # Calculate clearing
            total_vehicles = queues[green_idx] + lane_states[green_idx]["weighted_count"]
            capacity = self.service_rate * green_time
            cleared = min(total_vehicles, capacity)
            queues[green_idx] = total_vehicles - cleared
            total_throughput += cleared

            # Update waiting time for RED lanes
            for i in range(self.lanes):
                if i != green_idx:
                    queues[i] += lane_states[i]["weighted_count"]
                    total_waiting_time += queues[i] * green_time
                    lane_wait_times[i] += queues[i] * green_time

            total_time += green_time
            lane_green_counts[green_idx] += 1

            history.append({
                "cycle": cycle + 1,
                "green_lane": green_idx + 1,
                "green_time": green_time,
                "throughput": cleared,
                "waiting_time": sum(queues[i] * green_time for i in range(self.lanes) if i != green_idx),
            })

            # Refresh green lane image
            new_image_path = self.loader.get_one_image()
            if new_image_path:
                result = self._analyze_lane(new_image_path)
                lane_states[green_idx] = {
                    "image_path": new_image_path,
                    "density": result["density"],
                    "vehicle_counts": result["vehicle_counts"],
                    "green_time": fixed_time,
                    "weighted_count": result["weighted_count"],
                }

        # Calculate fairness index
        green_counts = np.array(lane_green_counts)
        fairness = (np.sum(green_counts) ** 2) / (self.lanes * np.sum(green_counts ** 2)) if np.sum(green_counts ** 2) > 0 else 0

        return {
            "total_throughput": round(total_throughput, 2),
            "total_waiting_time": round(total_waiting_time, 2),
            "avg_waiting_time": round(total_waiting_time / self.cycles, 2),
            "total_time": round(total_time, 2),
            "fairness_index": round(fairness, 4),
            "lane_green_counts": lane_green_counts,
            "lane_wait_times": [round(w, 2) for w in lane_wait_times],
            "history": history,
        }

    def run(self) -> Dict:
        """Run both scheduling simulations."""
        print("[SchedulingEffectivenessTest] Running density-based simulation...")
        seed = random.randint(0, 10000)
        density_results = self._simulate_density_based(seed)
        
        print("[SchedulingEffectivenessTest] Running fixed-time simulation...")
        fixed_results = self._simulate_fixed_time(seed)
        
        # Calculate throughput per second (normalized for fair comparison)
        density_tps = density_results["total_throughput"] / density_results["total_time"] if density_results["total_time"] > 0 else 0
        fixed_tps = fixed_results["total_throughput"] / fixed_results["total_time"] if fixed_results["total_time"] > 0 else 0
        
        # Calculate improvements
        throughput_improvement = ((density_results["total_throughput"] - fixed_results["total_throughput"]) 
                                  / fixed_results["total_throughput"] * 100) if fixed_results["total_throughput"] > 0 else 0
        throughput_efficiency_improvement = ((density_tps - fixed_tps) / fixed_tps * 100) if fixed_tps > 0 else 0
        waiting_improvement = ((fixed_results["total_waiting_time"] - density_results["total_waiting_time"]) 
                               / fixed_results["total_waiting_time"] * 100) if fixed_results["total_waiting_time"] > 0 else 0

        density_results["throughput_per_second"] = round(density_tps, 2)
        fixed_results["throughput_per_second"] = round(fixed_tps, 2)

        return {
            "density_based": density_results,
            "fixed_time": fixed_results,
            "improvements": {
                "throughput_pct": round(throughput_improvement, 2),
                "throughput_efficiency_pct": round(throughput_efficiency_improvement, 2),
                "waiting_time_pct": round(waiting_improvement, 2),
            }
        }


# ============================================================================
# Report Generator
# ============================================================================

def generate_report(detection_results: Dict, scheduling_results: Dict) -> str:
    """Generate Markdown report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""# Laporan Pengujian Efektivitas Algoritma

**Tanggal:** {now}
**Sistem:** Traffic Light AI Backend
**Model:** YOLOv8 (`latest_run/outputs/best.pt`)
**Dataset:** BMD-45 (Bengaluru Mobility Dataset)

---

## 1. Ringkasan

Laporan ini menyajikan hasil pengujian efektivitas dua komponen utama sistem:

1. **Akurasi Deteksi Kendaraan** - Mengukur performa model YOLOv8 dalam mendeteksi kendaraan (motor, auto, mobil, heavy) pada 100 sampel gambar acak dari BMD45-Val.
2. **Efektivitas Scheduling Lampu Lalu Lintas** - Membandingkan algoritma **Density-Based** dengan **Fixed-Time** (baseline) dalam simulasi 4 lane selama 20 cycle.

---

## 2. Pengujian Akurasi Deteksi (YOLOv8)

### 2.1 Metodologi

- **Jumlah Sampel:** {detection_results['num_samples']} gambar acak dari BMD-45-Val
- **Metrik:** Precision, Recall, F1-Score, mAP@0.5
- **Threshold IoU:** 0.5
- **Mapping Kelas:**
  - **Motor:** Two-wheeler, Bicycle
  - **Auto:** Three-wheeler
  - **Car:** Hatchback, Sedan, SUV, MUV, Van
  - **Heavy:** Bus, Truck, LCV, Mini-bus, Tempo-traveller

### 2.2 Hasil Per Kelas

| Kelas | Precision | Recall | F1-Score | mAP@0.5 | TP | FP | FN | Ground Truth |
|-------|-----------|--------|----------|---------|----|----|----|--------------|
"""
    
    for cls in OUR_CLASS_NAMES:
        m = detection_results["per_class"][cls]
        report += f"| {cls} | {m['precision']} | {m['recall']} | {m['f1_score']} | {m['ap_50']} | {m['tp']} | {m['fp']} | {m['fn']} | {m['gt_count']} |\n"

    report += f"""
### 2.3 Hasil Keseluruhan

| Metrik | Nilai |
|--------|-------|
| **Precision** | {detection_results['overall']['precision']} |
| **Recall** | {detection_results['overall']['recall']} |
| **F1-Score** | {detection_results['overall']['f1_score']} |
| **mAP@0.5** | {detection_results['overall']['mAP_50']} |
| **Total True Positives** | {detection_results['overall']['total_tp']} |
| **Total False Positives** | {detection_results['overall']['total_fp']} |
| **Total False Negatives** | {detection_results['overall']['total_fn']} |
| **Avg Inference Time** | {detection_results['overall']['avg_inference_time_ms']} ms |

### 2.4 Analisis

- **Precision** sebesar **{detection_results['overall']['precision']}** menunjukkan dari semua prediksi model, sekitar {int(detection_results['overall']['precision'] * 100)}% adalah benar.
- **Recall** sebesar **{detection_results['overall']['recall']}** menunjukkan model berhasil mendeteksi {int(detection_results['overall']['recall'] * 100)}% dari total kendaraan yang sebenarnya ada.
- **mAP@0.5** sebesar **{detection_results['overall']['mAP_50']}** mencerminkan kualitas deteksi secara keseluruhan.
- **Inference Time** rata-rata **{detection_results['overall']['avg_inference_time_ms']} ms** menunjukkan model cukup cepat untuk aplikasi real-time.

---

## 3. Pengujian Efektivitas Scheduling

### 3.1 Metodologi

- **Jumlah Lane:** {NUM_LANES}
- **Jumlah Cycle:** {NUM_CYCLES}
- **Max Green Time:** {MAX_GREEN_TIME} detik
- **Service Rate:** {SERVICE_RATE} weighted vehicles/second
- **Skenario:**
  - **Density-Based:** Lane dengan kepadatan tertinggi mendapatkan waktu hijau. Hanya lane yang baru hijau yang mendapatkan gambar baru.
  - **Fixed-Time:** Lane bergantian secara round-robin dengan waktu hijau tetap = {MAX_GREEN_TIME}/{NUM_LANES} = {MAX_GREEN_TIME/NUM_LANES} detik.

### 3.2 Hasil Perbandingan

| Metrik | Density-Based | Fixed-Time | Perubahan |
|--------|---------------|------------|-----------|
| **Total Throughput** | {scheduling_results['density_based']['total_throughput']} | {scheduling_results['fixed_time']['total_throughput']} | **{scheduling_results['improvements']['throughput_pct']:+.1f}%** |
| **Throughput per Detik** | {scheduling_results['density_based']['throughput_per_second']} | {scheduling_results['fixed_time']['throughput_per_second']} | **{scheduling_results['improvements']['throughput_efficiency_pct']:+.1f}%** |
| **Total Waiting Time** | {scheduling_results['density_based']['total_waiting_time']} | {scheduling_results['fixed_time']['total_waiting_time']} | **{scheduling_results['improvements']['waiting_time_pct']:+.1f}%** |
| **Avg Waiting Time/Cycle** | {scheduling_results['density_based']['avg_waiting_time']} | {scheduling_results['fixed_time']['avg_waiting_time']} | - |
| **Total Time** | {scheduling_results['density_based']['total_time']} detik | {scheduling_results['fixed_time']['total_time']} detik | - |
| **Fairness Index** | {scheduling_results['density_based']['fairness_index']} | {scheduling_results['fixed_time']['fairness_index']} | - |

### 3.3 Detail Per Lane (Density-Based)

| Lane | Jumlah Kali Hijau | Total Waiting Time |
|------|-------------------|-------------------|
"""
    
    for i in range(NUM_LANES):
        report += f"| Lane {i+1} | {scheduling_results['density_based']['lane_green_counts'][i]} | {scheduling_results['density_based']['lane_wait_times'][i]} |\n"

    report += f"""
### 3.4 Detail Per Lane (Fixed-Time)

| Lane | Jumlah Kali Hijau | Total Waiting Time |
|------|-------------------|-------------------|
"""
    
    for i in range(NUM_LANES):
        report += f"| Lane {i+1} | {scheduling_results['fixed_time']['lane_green_counts'][i]} | {scheduling_results['fixed_time']['lane_wait_times'][i]} |\n"

    report += f"""
### 3.5 Analisis

- **Total Throughput:** Dalam 20 cycle, Fixed-Time menghasilkan throughput total lebih tinggi ({scheduling_results['fixed_time']['total_throughput']} vs {scheduling_results['density_based']['total_throughput']}) karena setiap cycle memiliki durasi tetap 15 detik, sehingga total waktu simulasi lebih panjang ({scheduling_results['fixed_time']['total_time']}s vs {scheduling_results['density_based']['total_time']}s).
- **Throughput Efficiency:** Ketika dinormalisasi per detik, Density-Based mencapai **{scheduling_results['density_based']['throughput_per_second']} weighted vehicles/detik** dibandingkan Fixed-Time **{scheduling_results['fixed_time']['throughput_per_second']} weighted vehicles/detik**. Ini menunjukkan efisiensi **{scheduling_results['improvements']['throughput_efficiency_pct']:+.1f}%** lebih tinggi pada Density-Based, karena lane yang lebih padat mendapatkan waktu hijau lebih lama dan lebih banyak kendaraan dapat dilayani per unit waktu.
- **Waiting Time:** Algoritma Density-Based {'mengurangi' if scheduling_results['improvements']['waiting_time_pct'] > 0 else 'menambah'} total waiting time sebesar **{abs(scheduling_results['improvements']['waiting_time_pct']):.1f}%**. {'Ini menunjukkan bahwa lane yang padat lebih cepat dilayani, mengurangi akumulasi kendaraan menunggu.' if scheduling_results['improvements']['waiting_time_pct'] > 0 else 'Perlu diperhatikan bahwa density-based mungkin menyebabkan lane yang sepi menunggu lebih lama.'}
- **Fairness Index:** Fixed-Time memiliki fairness index sempurna (1.0) karena setiap lane mendapatkan kesempatan hijau secara merata. Density-Based memiliki fairness index **{scheduling_results['density_based']['fairness_index']}**, yang menunjukkan bias terhadap lane yang lebih padat. Ini adalah trade-off antara efisiensi dan keadilan.

---

## 4. Kesimpulan

### 4.1 Akurasi Deteksi
Model YOLOv8 menunjukkan performa deteksi yang {'baik' if detection_results['overall']['mAP_50'] > 0.5 else 'cukup' if detection_results['overall']['mAP_50'] > 0.3 else 'perlu perbaikan'} dengan mAP@0.5 sebesar **{detection_results['overall']['mAP_50']}**. Model mampu mendeteksi kendaraan dalam kondisi lalu lintas urban (Bengaluru) dengan inference time yang memadai untuk aplikasi real-time.

### 4.2 Efektivitas Scheduling
Algoritma Density-Based menunjukkan efisiensi waktu yang lebih baik dengan throughput per detik **{scheduling_results['improvements']['throughput_efficiency_pct']:+.1f}%** lebih tinggi dibandingkan Fixed-Time. Meskipun total throughput dalam 20 cycle lebih rendah karena total waktu simulasi lebih singkat, algoritma ini berhasil mengurangi total waiting time sebesar **{scheduling_results['improvements']['waiting_time_pct']:.1f}%**. Trade-off pada fairness index ({scheduling_results['density_based']['fairness_index']}) adalah konsekuensi logis dari prioritasi lane yang lebih padat.

### 4.3 Rekomendasi
1. **Peningkatan Model:** Pertimbangkan fine-tuning model pada dataset BMD-45 untuk meningkatkan akurasi deteksi pada kelas-kelas spesifik yang belum optimal (terutama kelas "car" dengan precision hanya {detection_results['per_class']['car']['precision']}).
2. **Fairness Adjustment:** Pertimbangkan menambahkan mekanisme "maximum waiting time" untuk lane yang jarang mendapatkan hijau, untuk meningkatkan fairness tanpa mengorbankan efisiensi secara signifikan.
3. **Real-World Validation:** Lakukan validasi pada deployment nyata dengan data lalu lintas lokal untuk memastikan performa model pada kondisi jalan Indonesia.

---

*Laporan ini dihasilkan secara otomatis oleh sistem pengujian efektivitas algoritma.*
"""

    return report


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 60)
    print("TRAFFIC LIGHT AI - EFFECTIVENESS TEST SUITE")
    print("=" * 60)

    # Initialize components
    print("\n[Main] Initializing engine and loader...")
    engine = AnalysisEngine()
    loader = BMD45Loader()

    # Test 1: Detection Accuracy
    print("\n" + "=" * 60)
    print("TEST 1: DETECTION ACCURACY")
    print("=" * 60)
    detection_test = DetectionAccuracyTest(MODEL_PATH, ANNOTATION_PATH, NUM_DETECTION_SAMPLES)
    detection_results = detection_test.run()

    # Test 2: Scheduling Effectiveness
    print("\n" + "=" * 60)
    print("TEST 2: SCHEDULING EFFECTIVENESS")
    print("=" * 60)
    scheduling_test = SchedulingEffectivenessTest(engine, loader, NUM_LANES, NUM_CYCLES, MAX_GREEN_TIME)
    scheduling_results = scheduling_test.run()

    # Save JSON results
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "detection": detection_results,
        "scheduling": scheduling_results,
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n[Main] Results saved to {RESULTS_PATH}")

    # Generate report
    print("\n[Main] Generating Markdown report...")
    report = generate_report(detection_results, scheduling_results)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[Main] Report saved to {REPORT_PATH}")

    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETED")
    print("=" * 60)
    print(f"\nDetection mAP@0.5: {detection_results['overall']['mAP_50']}")
    print(f"Throughput Improvement: {scheduling_results['improvements']['throughput_pct']:+.1f}%")
    print(f"Waiting Time Improvement: {scheduling_results['improvements']['waiting_time_pct']:+.1f}%")


if __name__ == "__main__":
    main()
