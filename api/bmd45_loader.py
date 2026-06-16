import os
import json
import random
import time
from pathlib import Path
from typing import List, Dict, Optional
from huggingface_hub import hf_hub_download, HfApi
from backend_logs import backend_logs

REPO_ID = "iisc-aim/BMD-45"
SPLITS = {"train": "BMD-45-Train", "val": "BMD-45-Val"}
ANNOTATION_FILE = "_annotations.coco.json"

# Local cache directory
CACHE_DIR = Path(__file__).parent / ".cache" / "bmd45"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class BMD45Loader:
    def __init__(self):
        self.annotations_cache: Dict[str, any] = {}
        self.image_list: List[Dict] = []
        self._annotations_downloaded = False
        self._download_annotations()

    def _download_annotations(self):
        """Download COCO annotation files from BMD45 and build image list."""
        print("[BMD45Loader] Downloading annotations...")
        backend_logs.add("INFO", "BMD45Loader", "Downloading BMD45 annotations")
        for split, split_dir in SPLITS.items():
            remote_path = f"{split_dir}/{ANNOTATION_FILE}"
            local_path = hf_hub_download(
                repo_id=REPO_ID,
                repo_type="dataset",
                filename=remote_path,
                local_dir=str(CACHE_DIR),
                local_dir_use_symlinks=False,
            )
            with open(local_path, "r", encoding="utf-8") as f:
                coco_data = json.load(f)
            self.annotations_cache[split] = coco_data
            print(f"[BMD45Loader] {split}: {len(coco_data.get('images', []))} images listed")
            backend_logs.add(
                "INFO",
                "BMD45Loader",
                f"BMD45 {split} annotations loaded",
                details={"split": split, "image_count": len(coco_data.get('images', []))},
            )

        # Build flat list of all images with their remote paths
        repo_files = set(HfApi().list_repo_files(repo_id=REPO_ID, repo_type="dataset"))
        for split, coco_data in self.annotations_cache.items():
            split_dir = SPLITS[split]
            for img in coco_data.get("images", []):
                file_name = img.get("file_name", "")
                # Normalize path
                remote_candidates = [
                    f"{split_dir}/{file_name}",
                    file_name,
                ]
                remote_path = None
                for cand in remote_candidates:
                    if cand in repo_files:
                        remote_path = cand
                        break
                if not remote_path:
                    remote_path = remote_candidates[0]

                self.image_list.append({
                    "split": split,
                    "image_id": img["id"],
                    "file_name": file_name,
                    "remote_path": remote_path,
                })

        random.shuffle(self.image_list)
        print(f"[BMD45Loader] Total images available: {len(self.image_list)}")
        backend_logs.add(
            "INFO",
            "BMD45Loader",
            "BMD45 image catalog ready",
            details={"image_count": len(self.image_list)},
        )

    def download_images(self, count: int) -> List[str]:
        """Download N random images from BMD45. Returns list of local file paths."""
        if count > len(self.image_list):
            # Allow repeats if we need more images than available
            selected = random.choices(self.image_list, k=count)
        else:
            selected = random.sample(self.image_list, count)

        local_paths = []
        for item in selected:
            try:
                local_path = hf_hub_download(
                    repo_id=REPO_ID,
                    repo_type="dataset",
                    filename=item["remote_path"],
                    local_dir=str(CACHE_DIR),
                    local_dir_use_symlinks=False,
                )
                local_paths.append(str(local_path))
                print(f"[BMD45Loader] Downloaded: {item['file_name']}")
                backend_logs.add(
                    "INFO",
                    "BMD45Loader",
                    f"Downloaded BMD45 image {item['file_name']}",
                    details={"file_name": item["file_name"], "split": item["split"]},
                )
            except Exception as e:
                print(f"[BMD45Loader] Failed to download {item['remote_path']}: {e}")
                backend_logs.add(
                    "ERROR",
                    "BMD45Loader",
                    f"Failed to download BMD45 image {item['remote_path']}",
                    details={"remote_path": item["remote_path"]},
                    exc=e,
                )
                # Try to get another image as fallback
                fallback = random.choice(self.image_list)
                try:
                    local_path = hf_hub_download(
                        repo_id=REPO_ID,
                        repo_type="dataset",
                        filename=fallback["remote_path"],
                        local_dir=str(CACHE_DIR),
                        local_dir_use_symlinks=False,
                    )
                    local_paths.append(str(local_path))
                except Exception as e2:
                    print(f"[BMD45Loader] Fallback also failed: {e2}")
                    backend_logs.add(
                        "ERROR",
                        "BMD45Loader",
                        "Fallback BMD45 image download failed",
                        details={"remote_path": fallback["remote_path"]},
                        exc=e2,
                    )
                    local_paths.append(None)

        return local_paths

    def get_one_image(self) -> str:
        """Download a single random image."""
        paths = self.download_images(1)
        return paths[0] if paths else None
