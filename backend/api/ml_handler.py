import os
import cv2
import numpy as np
import keras
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from django.conf import settings

# --- 1. GLOBAL MODEL LOADING (Runs once at startup) ---

BASE_DIR = settings.BASE_DIR
MODEL_PATH = os.path.join(BASE_DIR, 'api', 'ml_models', 'xception_deepfake_image_5o.h5')
DETECTOR_PATH = os.path.join(BASE_DIR, 'api', 'ml_models', 'detector.tflite')

print("⏳ Loading Image ML Models... This may take a moment.")

try:
    deepfake_model = keras.models.load_model(MODEL_PATH)
    print("✅ Deepfake Image Model Loaded.")
except Exception as e:
    print(f"❌ Failed to load Deepfake Image Model: {e}")
    deepfake_model = None

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

def predict_single_face(img_bgr):
    """
    Takes a BGR numpy array to match the Kaggle author's training format,
    resizes it to 224x224, normalizes to [0, 1], and returns confidence.
    """
    # 1. Resize the BGR image
    img_resized = cv2.resize(img_bgr, (224, 224))
    
    # 2. Preprocessing & Normalization
    img_array = np.array(img_resized, dtype=np.float32)
    img_array = img_array / 255.0  
    img_array = np.expand_dims(img_array, axis=0)
    
    # 3. Prediction
    prediction = deepfake_model.predict(img_array, verbose=0)
    score = float(prediction[0][0])

    # 4. Logic: > 0.5 is FAKE
    label = "FAKE" if score > 0.5 else "REAL"
    confidence = score if score > 0.5 else (1.0 - score)
    
    return {
        "label": label,
        "confidence": float(confidence),
        "raw_score": float(score)
    }

def analyze_image_pipeline(image_path):
    if deepfake_model is None or detector is None:
        return {"error": "Models not loaded correctly"}

    # Read Image in BGR (For the Model)
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        return {"error": "Could not read image file"}
    
    # Convert to RGB (Strictly for MediaPipe Face Detection)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w, _ = img_rgb.shape
    
    results = []

    SIZE_THRESHOLD = 500
    should_detect_faces = (w > SIZE_THRESHOLD or h > SIZE_THRESHOLD)

    faces_found = 0

    if should_detect_faces:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        detection_result = detector.detect(mp_image)
        
        if detection_result.detections:
            faces_found = len(detection_result.detections)
            print(f"🔍 Detected {faces_found} faces.")

            for i, detection in enumerate(detection_result.detections):
                bbox = detection.bounding_box
                
                x, y, bw, bh = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height
                pad_w, pad_h = int(bw * 0.25), int(bh * 0.25)
                
                x1, y1 = max(0, x - pad_w), max(0, y - pad_h)
                x2, y2 = min(w, x + bw + pad_w), min(h, y + bh + pad_h)

                # CRITICAL CHANGE: We crop from the BGR image, not the RGB image!
                face_crop_bgr = img_bgr[y1:y2, x1:x2]
                
                if face_crop_bgr.size > 0:
                    res = predict_single_face(face_crop_bgr)
                    res['face_index'] = i + 1
                    results.append(res)
        else:
            print("⚠️ Large image but no faces found. Running full frame.")
    
    # Fallback if no faces found
    if not results:
        res = predict_single_face(img_bgr) # Pass the BGR image
        res['note'] = "Full Frame Analysis"
        results.append(res)

    overall_status = "REAL"
    avg_confidence = 0
    
    for r in results:
        if r['label'] == "FAKE":
            overall_status = "FAKE"
            avg_confidence = r['confidence']
            break 
        else:
            avg_confidence += r['confidence']
    
    if overall_status == "REAL" and len(results) > 0:
        avg_confidence /= len(results)

    return {
        "status": overall_status,
        "confidence": round(avg_confidence * 100, 2),
        "details": results,
        "faces_detected": faces_found
    }