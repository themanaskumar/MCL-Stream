import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow import keras
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from django.conf import settings

# --- 1. GLOBAL MODEL LOADING ---
BASE_DIR = settings.BASE_DIR

# This single model file contains BOTH the Xception (CNN) and the LSTM (RNN)
VIDEO_MODEL_PATH = os.path.join(BASE_DIR, 'api', 'ml_models', 'deepfake_video_lstm_v2.keras')
DETECTOR_PATH = os.path.join(BASE_DIR, 'api', 'ml_models', 'detector.tflite')

SEQUENCE_LENGTH = 20
FRAME_SIZE = (300, 300)

print("⏳ Loading CNN-LSTM Video Model...")

try:
    # --- BULLETPROOF LOAD: Rebuild Architecture & Inject Weights ---
    
    # 1. Rebuild the Xception Base
    base_xception = keras.applications.Xception(
        include_top=False, 
        weights=None, 
        input_shape=(FRAME_SIZE[0], FRAME_SIZE[1], 3),
        pooling='avg'
    )
    base_xception.trainable = False

    # 2. Rebuild the Spatial-Temporal Network
    video_input = keras.layers.Input(shape=(SEQUENCE_LENGTH, FRAME_SIZE[0], FRAME_SIZE[1], 3))
    encoded_frames = keras.layers.TimeDistributed(base_xception)(video_input)
    lstm_out = keras.layers.LSTM(128)(encoded_frames)
    
    x = keras.layers.Dropout(0.5)(lstm_out)
    x = keras.layers.Dense(64, activation='relu')(x)
    output = keras.layers.Dense(1, activation='sigmoid')(x)

    video_model = keras.Model(inputs=video_input, outputs=output)
    
    # 3. Inject your trained weights into the fresh architecture
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
    """Detects a face, crops it with padding, and resizes to 300x300."""
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    detection_result = detector.detect(mp_image)
    
    h, w, _ = img_rgb.shape
    
    if detection_result.detections:
        # Take the most prominent face
        best_face = max(detection_result.detections, key=lambda x: x.categories[0].score)
        bbox = best_face.bounding_box
        
        x, y, bw, bh = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height
        pad_w, pad_h = int(bw * 0.25), int(bh * 0.25)
        
        x1, y1 = max(0, x - pad_w), max(0, y - pad_h)
        x2, y2 = min(w, x + bw + pad_w), min(h, y + bh + pad_h)
        
        face_crop = img_rgb[y1:y2, x1:x2]
        if face_crop.size > 0:
            return cv2.resize(face_crop, FRAME_SIZE)
            
    # Fallback: Center crop if MediaPipe briefly loses the face
    center_crop = img_rgb[h//4:h - h//4, w//4:w - w//4]
    if center_crop.size > 0:
        return cv2.resize(center_crop, FRAME_SIZE)
    return cv2.resize(img_rgb, FRAME_SIZE)


def analyze_video_pipeline(video_path):
    """
    Advanced Pipeline: Extracts frames at 3 FPS, chunks them into 20-frame sequences,
    runs batch prediction, and averages the results.
    """
    if video_model is None or detector is None:
        return {"error": "Models not loaded correctly"}

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Could not open video file"}

    # 1. Calculate Frame Skip for 3 FPS
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    if original_fps == 0 or np.isnan(original_fps):
        original_fps = 30 # Fallback to 30 FPS if metadata is missing
        
    TARGET_FPS = 3
    frame_skip = max(1, int(original_fps / TARGET_FPS))

    processed_frames = []
    frame_count = 0
    
    # Optional: Set a max frame limit (e.g., 120 frames = 40 seconds of video) 
    # to prevent your computer's RAM from crashing on massive files.
    MAX_TOTAL_FRAMES = 120 

    # 2. Extract at 3 FPS
    while cap.isOpened() and len(processed_frames) < MAX_TOTAL_FRAMES:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Only process 1 frame every 'frame_skip' interval
        if frame_count % frame_skip == 0:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            processed_face = extract_face(img_rgb)
            processed_face = (processed_face / 255.0).astype(np.float32)
            processed_frames.append(processed_face)
            
        frame_count += 1

    cap.release()

    if len(processed_frames) == 0:
        return {"error": "No valid frames could be extracted from the video."}

    # 3. Chunking Logic 
    chunks = []
    
    # Split the extracted frames into chunks of exactly 20 (SEQUENCE_LENGTH)
    for i in range(0, len(processed_frames), SEQUENCE_LENGTH):
        chunk = processed_frames[i:i + SEQUENCE_LENGTH]
        
        # Temporal Padding: If the last chunk is too short, duplicate its final frame
        while len(chunk) < SEQUENCE_LENGTH:
            chunk.append(chunk[-1] if chunk else np.zeros((*FRAME_SIZE, 3), dtype=np.float32))
            
        chunks.append(chunk)

    # 4. Batch Prediction
    # Convert list of chunks into a single 5D Tensor: (Num_Chunks, 20, 300, 300, 3)
    input_data = np.array(chunks)

    # The model predicts on ALL chunks simultaneously, returning an array of scores
    predictions = video_model.predict(input_data, verbose=0)
    
    # 5. Average the Results
    # predictions looks like [[0.12], [0.85], [0.44]]
    avg_score = float(np.mean(predictions))
    
    # Logic: Assuming 0 = Fake, 1 = Real
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