import uvicorn
import tempfile
import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from yolov8_inference import run_inference_on_image
from chair_classification import classify_json

app = FastAPI(title="DesignableAI - Chair Analyzer")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (adjust in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze-chair")
async def analyze_chair(file: UploadFile = File(...)):
    # Accept only images (basic check)
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    
    # Save uploaded image temporarily
    try:
        suffix = os.path.splitext(file.filename)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            content = await file.read()
            tmp.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")
    
    try:
        # Run YOLO inference (this returns the list of detection dicts)
        detections = run_inference_on_image(temp_path, conf_thresh=0.25)
        
        # Optionally: save raw detections for debugging
        # with open("last_raw_detections.json","w") as f: json.dump(detections,f,indent=2)
        
        # Pass the detection list directly into the classifier
        result = classify_json(detections, image_id=file.filename)
        
        # Clean up the temporary image
        try:
            os.remove(temp_path)
        except:
            pass
        
        return JSONResponse(content=result)
    except Exception as e:
        # cleanup and return error
        try:
            os.remove(temp_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Inference or classification failed: {e}")

if __name__ == "__main__":
    uvicorn.run("main_app:app", host="0.0.0.0", port=8000, reload=True)