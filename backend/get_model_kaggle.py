import os
import requests

# 1. Set the destination path exactly where Django expects it
# Path: backend/api/ml_models/detector.tflite
destination_dir = os.path.join("api", "ml_models")
destination_file = os.path.join(destination_dir, "detector.tflite")

# Ensure the folder exists
if not os.path.exists(destination_dir):
    os.makedirs(destination_dir)

# 2. URL for the MediaPipe Face Detector (Short Range - TFLite version)
# This is the official, working link from Google MediaPipe
url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"

print(f"⬇️  Downloading correct TFLite model to: {destination_file}...")

try:
    response = requests.get(url)
    if response.status_code == 200:
        with open(destination_file, 'wb') as f:
            f.write(response.content)
        print("✅ Success! The model is now ready for your Django backend.")
    else:
        print(f"❌ Failed to download. Status code: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")