from ultralytics import YOLO
import os
import torch # We'll check for mps device availability

# --- Configuration ---
# Set the path to your data.yaml file.
# We assume the 'DesignableAI-1' folder (your dataset) is in the same directory as this script.
DATA_YAML_PATH = './DesignableAI-3/data.yaml' 

# Determine the device for training (GPU/MPS for speed, or CPU for fallback)
if torch.cuda.is_available():
    # If using a PC with an NVIDIA GPU
    DEVICE = 0 
elif torch.backends.mps.is_available():
    # If using a Mac with Apple Silicon (M1/M2/M3)
    DEVICE = 'mps'
else:
    # Fallback to CPU if no compatible GPU is found (training will be slow)
    DEVICE = 'cpu'

print(f"Using device: {DEVICE}")

# --- 1. Load the base model ---
# Using the nano segmentation model for a quick start.
model = YOLO('yolov8n-seg.pt')

# --- 2. Start the training process ---
print("Starting YOLOv8 Segmentation Model Training...")

try:
    results = model.train(
        data=DATA_YAML_PATH,
        epochs=100,  # A good starting point
        imgsz=640,   # Standard YOLO size
        batch=8,     # Adjust based on your GPU memory (8 is conservative)
        device=DEVICE, 
        project='yolo_chair_training',
        name='v1'
    )
    
    print("\nTraining complete!")
    print("Results saved to: yolo_chair_training/v1")

except FileNotFoundError:
    print(f"\nERROR: Data YAML file not found at {DATA_YAML_PATH}.")
    print("Please make sure your folder structure looks like this:")
    print("  /your_project_root")
    print("    |-- train_segmentation.py (this file)")
    print("    |-- DesignableAI-3/")
    print("          |-- data.yaml")
    print("          |-- train/")
    print("          |-- valid/")

except Exception as e:
    print(f"\nAn unexpected error occurred during training: {e}")
    print("Please check your environment setup and data configuration.")