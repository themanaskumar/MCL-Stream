import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.applications.xception import preprocess_input
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from django.conf import settings

# --- 1. GLOBAL MODEL LOADING ---
BASE_DIR = settings.BASE_DIR

VIDEO_MODEL_PATH = os.path.join(BASE_DIR, 'api', 'ml_models', 'deepfake_video_lstm_v2.keras')
DETECTOR_PATH = os.path.join(BASE_DIR, 'api', 'ml_models', 'detector.tflite')

SEQUENCE_LENGTH = 20
FRAME_SIZE = (300, 300)

print("⏳ Loading CNN-LSTM Video Model...")

try:
    base_xception = keras.applications.Xception(
        include_top=False, 
        weights=None, 
        input_shape=(FRAME_SIZE[0], FRAME_SIZE[1], 3),
        pooling='avg'
    )
    base_xception.trainable = False

    video_input = keras.layers.Input(shape=(SEQUENCE_LENGTH, FRAME_SIZE[0], FRAME_SIZE[1], 3))
    encoded_frames = keras.layers.TimeDistributed(base_xception)(video_input)
    lstm_out = keras.layers.LSTM(128)(encoded_frames)
    
    x = keras.layers.Dropout(0.5)(lstm_out)
    x = keras.layers.Dense(64, activation='relu')(x)
    output = keras.layers.Dense(1, activation='sigmoid')(x)

    video_model = keras.Model(inputs=video_input, outputs=output)
    video_model.load_weights(VIDEO_MODEL_PATH)
    
    print("✅ CNN-LSTM Video Architecture rebuilt and weights loaded successfully.")
except Exception as e:
    print(f"❌ Failed to load Video Model: {e}")
    video_model = None

try:
    base_options = python.BaseOptions(model_asset_path=DETECTOR_PATH)
    options = vision.FaceDetectorOptions(base_options=base_options, min_detection_confidence=0.35)
    detector = vision.FaceDetector.create_from_options(options)
    print("✅ Face Detector Loaded for Video.")
except Exception as e:
    print(f"❌ Failed to load Face Detector: {e}")
    detector = None

# --- 2. CORE VIDEO FUNCTIONS ---

def extract_face(img_rgb):
    """Detects a face, crops it with padding, and resizes to 300x300. Returns None if no face found."""
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    detection_result = detector.detect(mp_image)
    
    h, w, _ = img_rgb.shape
    
    if detection_result.detections:
        best_face = max(detection_result.detections, key=lambda x: x.categories[0].score)
        bbox = best_face.bounding_box
        
        x, y, bw, bh = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height
        pad_w, pad_h = int(bw * 0.25), int(bh * 0.25)
        
        x1, y1 = max(0, x - pad_w), max(0, y - pad_h)
        x2, y2 = min(w, x + bw + pad_w), min(h, y + bh + pad_h)
        
        face_crop = img_rgb[y1:y2, x1:x2]
        if face_crop.size > 0:
            return cv2.resize(face_crop, FRAME_SIZE)
            
    return None

def analyze_video_pipeline(video_path):
    if video_model is None or detector is None:
        return {"error": "Models not loaded correctly"}

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Could not open video file"}

    original_fps = cap.get(cv2.CAP_PROP_FPS)
    if original_fps == 0 or np.isnan(original_fps):
        original_fps = 30 
        
    TARGET_FPS = 3
    frame_skip = max(1, int(original_fps / TARGET_FPS))

    processed_frames = []
    frame_count = 0
    MAX_TOTAL_FRAMES = 120 

    while cap.isOpened() and len(processed_frames) < MAX_TOTAL_FRAMES:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % frame_skip == 0:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            raw_face = extract_face(img_rgb)
            
            if raw_face is not None:
                processed_face = preprocess_input(raw_face.astype(np.float32))
                processed_frames.append(processed_face)
            
        frame_count += 1

    cap.release()

    if len(processed_frames) == 0:
        return {"error": "No valid faces could be extracted from the video."}

    chunks = []
    
    for i in range(0, len(processed_frames), SEQUENCE_LENGTH):
        chunk = processed_frames[i:i + SEQUENCE_LENGTH]
        while len(chunk) < SEQUENCE_LENGTH:
            chunk.append(chunk[-1] if chunk else np.zeros((*FRAME_SIZE, 3), dtype=np.float32))
        chunks.append(chunk)

    input_data = np.array(chunks)
    predictions = video_model.predict(input_data, verbose=0)
    avg_score = float(np.mean(predictions))
    
    label = "REAL" if avg_score > 0.5 else "FAKE"
    confidence = avg_score if avg_score > 0.5 else (1.0 - avg_score)

    return {
        "status": label,
        "confidence": round(confidence * 100, 2),
        "raw_score": avg_score,
        "frames_analyzed": len(processed_frames),
        "chunks_processed": len(chunks),
        "architecture_used": "CNN-LSTM Hybrid (3 FPS Chunking)",
        "note": f"Extracted at 3 FPS. Evaluated {len(chunks)} sequence(s) of 20 frames."
    }