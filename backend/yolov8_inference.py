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
MODEL_PATH = os.path.join(PROJECT_ROOT, "Roboflow", "yolo_chair_training", "v13", "weights", "best.pt")

# Load once at import time
_model = None

def get_model():
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
    return _model

def run_inference_on_image(image_path: str, conf_thresh: float = 0.25) -> List[Dict]:
    """
    Returns a list of detections in the same structure you used before:
    [
      {"id": 1, "part_name": "Headrest", "confidence": 0.99, "normalized_bbox_xywh": [...], "mask_pixel_area_proxy": 1234},
      ...
    ]
    """
    model = get_model()
    results = model.predict(source=image_path, conf=conf_thresh, save=False, save_txt=False)
    extracted_data = []
    for r in results:
        # r.boxes and r.masks correspond to the predictions for that image
        # ensure r.boxes exists
        if not hasattr(r, "boxes") or len(r.boxes) == 0:
            continue

        for i in range(len(r.boxes)):
            box = r.boxes[i]
            # safeguard: some models return tensors, convert to python types
            try:
                class_id = int(box.cls)
            except Exception:
                # fallback if structure is different
                class_id = int(box.cls.cpu().numpy())

            try:
                conf = float(box.conf) if hasattr(box, "conf") else 0.0
            except:
                conf = float(box.conf.cpu().numpy())

            class_name = model.names.get(class_id, str(class_id))

            # normalized xywh
            # box.xywhn might be a tensor; convert safely
            try:
                xywhn = box.xywhn[0].tolist()
            except:
                # fallback: compute normalized from box.xyxy and image size
                try:
                    xyxy = box.xyxy[0].tolist()
                    # we could compute, but keep safe for now
                    xywhn = [0,0,0,0]
                except:
                    xywhn = [0,0,0,0]

            # mask area proxy (if masks exist)
            mask_area = 0
            if hasattr(r, "masks") and r.masks is not None:
                try:
                    mask = r.masks[i]
                    mask_area = int(np.sum(mask.data[0].cpu().numpy()))
                except Exception:
                    mask_area = 0

            extracted_data.append({
                "id": len(extracted_data) + 1,
                "part_name": class_name,
                "confidence": round(conf, 4),
                "normalized_bbox_xywh": [round(x, 4) for x in xywhn],
                "mask_pixel_area_proxy": int(mask_area)
            })

    return extracted_data
