# yolov8_inference.py
from ultralytics import YOLO
import numpy as np
from typing import List, Dict
from PIL import Image
import os

# Path to your weights (update if needed)
#MODEL_PATH = "Roboflow/yolo_chair_training/v13/weights/best.pt"
# Get the directory of the current script (Backend folder)
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# Construct path to Roboflow folder (one level up from Backend)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
CHAIR_MODEL_PATH = os.path.join(PROJECT_ROOT, "Roboflow", "yolo_chair_training", "v13", "weights", "best.pt")
TABLE_MODEL_PATH = os.path.join(PROJECT_ROOT, "weights", "best.pt")

# Load once at import time
_models = {}

def get_model(furniture_type: str = "chair"):
    normalized = (furniture_type or "chair").strip().lower()
    model_key = normalized if normalized in {"chair", "table"} else "chair"
    model_path = CHAIR_MODEL_PATH if model_key == "chair" else TABLE_MODEL_PATH

    if model_key not in _models:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"YOLO weights not found for '{model_key}': {model_path}")
        _models[model_key] = YOLO(model_path)
    return _models[model_key]

def run_inference_on_image(image_path: str, conf_thresh: float = 0.25, furniture_type: str = "chair") -> List[Dict]:
    model = get_model(furniture_type=furniture_type)
    results = model.predict(source=image_path, conf=conf_thresh, save=False)
    extracted_data = []

    for r in results:
        if not hasattr(r, "boxes") or len(r.boxes) == 0:
            continue

        for i in range(len(r.boxes)):
            box = r.boxes[i]
            conf = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = model.names.get(class_id, str(class_id))

            # --- THE CRITICAL UPDATE: Extracting the Mask Polygon ---
            mask_data = []
            if hasattr(r, "masks") and r.masks is not None:
                try:
                    # r.masks.xy[i] returns a numpy array of [x, y] points for the i-th detection
                    points = r.masks.xy[i]
                    # Convert to a standard list for JSON/dictionary compatibility
                    mask_data = points.tolist() 
                except Exception as e:
                    print(f"Mask extraction error: {e}")
                    mask_data = []

            extracted_data.append({
                "id": len(extracted_data) + 1,
                "part_name": class_name,
                "confidence": round(conf, 4),
                "mask": mask_data,  # <--- THIS IS WHAT main.py IS LOOKING FOR
                "mask_pixel_area_proxy": len(mask_data) # Using point count as proxy
            })

    return extracted_data