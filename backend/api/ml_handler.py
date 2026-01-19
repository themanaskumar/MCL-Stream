import os
import cv2
import numpy as np
import keras
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from django.conf import settings

# --- 1. GLOBAL MODEL LOADING (Runs once at startup) ---

# Paths to your models
BASE_DIR = settings.BASE_DIR
MODEL_PATH = os.path.join(BASE_DIR, 'api', 'ml_models', 'deepfake_xception_tpu_v5.keras')
DETECTOR_PATH = os.path.join(BASE_DIR, 'api', 'ml_models', 'detector.tflite')

print("⏳ Loading ML Models... This may take a moment.")

# Load Deepfake Model
try:
    deepfake_model = keras.models.load_model(MODEL_PATH)
    print("✅ Deepfake Model Loaded.")
except Exception as e:
    print(f"❌ Failed to load Deepfake Model: {e}")
    deepfake_model = None

# Load Face Detector
try:
    base_options = python.BaseOptions(model_asset_path=DETECTOR_PATH)
    options = vision.FaceDetectorOptions(
        base_options=base_options,
        min_detection_confidence=0.35
    )
    detector = vision.FaceDetector.create_from_options(options)
    print("✅ Face Detector Loaded.")
except Exception as e:
    print(f"❌ Failed to load Face Detector: {e}")
    detector = None

# --- 2. CORE FUNCTIONS ---

def predict_single_face(img_rgb):
    """
    Takes an RGB numpy array (cropped face or full image),
    resizes it to 300x300, and returns confidence.
    """
    # Resize to model's expected input
    img_resized = cv2.resize(img_rgb, (300, 300))
    
    # Preprocessing
    img_array = keras.utils.img_to_array(img_resized)
    img_array = np.expand_dims(img_array, axis=0)
    
    # Prediction
    prediction = deepfake_model.predict(img_array, verbose=0)
    score = prediction[0][0] # Raw probability

    # Logic: Assuming 0 = Fake, 1 = Real (or vice versa based on your training)
    # Adjust this logic based on your specific training labels!
    # Common Xception setup: 0=Fake, 1=Real. 
    # If score > 0.5 -> Real.
    
    label = "REAL" if score > 0.5 else "FAKE"
    confidence = score if score > 0.5 else (1 - score)
    
    return {
        "label": label,
        "confidence": float(confidence), # Convert numpy float to python float
        "raw_score": float(score)
    }

def analyze_image_pipeline(image_path):
    """
    Main entry point. 
    1. Check image size.
    2. If large, detect faces -> crop -> predict.
    3. If small or no faces, predict full frame.
    """
    if deepfake_model is None or detector is None:
        return {"error": "Models not loaded correctly"}

    # Read Image
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        return {"error": "Could not read image file"}
    
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w, _ = img_rgb.shape
    
    results = []

    # Decide Strategy: Face Detect vs Direct
    SIZE_THRESHOLD = 500
    should_detect_faces = (w > SIZE_THRESHOLD or h > SIZE_THRESHOLD)

    faces_found = 0

    if should_detect_faces:
        # Create MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        detection_result = detector.detect(mp_image)
        
        if detection_result.detections:
            faces_found = len(detection_result.detections)
            print(f"🔍 Detected {faces_found} faces.")

            for i, detection in enumerate(detection_result.detections):
                bbox = detection.bounding_box
                
                # Coordinate extraction with padding
                x, y, bw, bh = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height
                pad_w, pad_h = int(bw * 0.25), int(bh * 0.25)
                
                x1, y1 = max(0, x - pad_w), max(0, y - pad_h)
                x2, y2 = min(w, x + bw + pad_w), min(h, y + bh + pad_h)

                face_crop = img_rgb[y1:y2, x1:x2]
                
                if face_crop.size > 0:
                    res = predict_single_face(face_crop)
                    res['face_index'] = i + 1
                    results.append(res)
        else:
            print("⚠️ Large image but no faces found. Running full frame.")
    
    # Fallback: If image is small OR no faces found in large image
    if not results:
        res = predict_single_face(img_rgb)
        res['note'] = "Full Frame Analysis"
        results.append(res)

    # Aggregation Logic: 
    # If ANY face is FAKE, the overall status is FAKE.
    overall_status = "REAL"
    avg_confidence = 0
    
    for r in results:
        if r['label'] == "FAKE":
            overall_status = "FAKE"
            avg_confidence = r['confidence']
            break # Fail fast (Security approach)
        else:
            # If all are real, take average confidence
            avg_confidence += r['confidence']
    
    if overall_status == "REAL" and len(results) > 0:
        avg_confidence /= len(results)

    return {
        "status": overall_status,
        "confidence": round(avg_confidence * 100, 2),
        "details": results,
        "faces_detected": faces_found
    }