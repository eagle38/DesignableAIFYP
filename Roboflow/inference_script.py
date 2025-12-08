import json
import numpy as np
from ultralytics import YOLO

# --- Configuration ---
# 1. Update this path to your trained model file
MODEL_PATH = 'yolo_chair_training/v13/weights/best.pt'



# 2. Update this path to a test image of your chair parts
# You can use a local path like 'path/to/my/test_chair_image.jpg'
# IMPORTANT: Make sure this image is correctly classified by your model.
IMAGE_PATH = 'DesignableAI-3/train/images/Eames_LoungeChair_1.jpg'




# ---------------------

def run_inference_and_extract_data(model_path: str, image_path: str):
    """
    Loads the YOLOv8 segmentation model, runs inference on an image, 
    and extracts structured data for each detected part.
    """
    try:
        # Load the custom trained model
        model = YOLO(model_path)
        print(f"Model loaded successfully from: {model_path}")
        
        # Run inference on the specified image
        # The 'save=True' option will save the resulting image with masks drawn
        results = model.predict(source=image_path, conf=0.25, save=True, save_txt=False)
        print(f"Inference completed on: {image_path}")

        extracted_data = []

        # Process results for each image (we only passed one image)
        for r in results:
            if r.masks is None:
                print("No segmentation masks found in the results.")
                continue

            # Iterate over each detection (each chair part)
            for i in range(len(r.boxes)):
                box = r.boxes[i]
                mask = r.masks[i]
                
                # Get the class ID and confidence
                class_id = int(box.cls)
                conf = round(float(box.conf), 4)
                
                # Get the class name from the model's names dictionary
                class_name = model.names[class_id]
                
                # Get the normalized bounding box (x_center, y_center, width, height)
                # We use normalized coords (0-1) for a concise representation.
                xywhn = box.xywhn[0].tolist() 
                
                # The mask data is often very large. For the LLM, we'll only extract
                # the count of pixels in the mask as a simple proxy for size.
                mask_area_pixels = np.sum(mask.data[0].cpu().numpy())

                extracted_data.append({
                    "id": i + 1,
                    "part_name": class_name,
                    "confidence": conf,
                    "normalized_bbox_xywh": [round(x, 4) for x in xywhn],
                    "mask_pixel_area_proxy": int(mask_area_pixels)
                })

        # Output the structured data
        if extracted_data:
            print("\n--- Structured Part Data (JSON) ---")
            json_output = json.dumps(extracted_data, indent=4)
            print(json_output)
            
            # Save the JSON data to a file for easy access in the next step
            with open('detected_chair_parts.json', 'w') as f:
                f.write(json_output)
            print("\nData saved to detected_chair_parts.json")
                 # ---------------------------
            # Step 1B: Post-processing stage
            # ---------------------------

            from backend.utils.image_processing import clean_yolo_output

            # Load the saved raw JSON so we can pass it to the post-processor
            with open('detected_chair_parts.json', 'r') as f:
                raw_data = json.load(f)

            # Get image size for pixel bbox estimates
            from PIL import Image
            try:
                with Image.open(image_path) as im:
                    img_size = (im.width, im.height)
            except:
                img_size = None

            # Run post-processing
            structured, concise_text, designer_text = clean_yolo_output(
                raw_data,
                image_size=img_size,
                low_confidence_threshold=0.5
            )

            # Save post-processed files
            with open('processed_detected_parts.json', 'w') as f:
                json.dump(structured, f, indent=2)
            print("\nProcessed structured data saved to processed_detected_parts.json")

            with open('summary_concise.txt', 'w') as f:
                f.write(concise_text)
            print("Concise summary saved to summary_concise.txt")

            with open('summary_designer.txt', 'w') as f:
                f.write(designer_text)
            print("Designer summary saved to summary_designer.txt")

            # Print sample
            print("\n=== Designer Summary Preview ===")
            print("\n".join(designer_text.splitlines()[:8]))
            print("...")


    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure you have installed 'ultralytics' and the file paths are correct.")

if __name__ == "__main__":
    run_inference_and_extract_data(MODEL_PATH, IMAGE_PATH)