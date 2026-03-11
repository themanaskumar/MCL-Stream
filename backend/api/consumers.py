import json
import base64
import cv2
import numpy as np
import tempfile
import tensorflow as tf
import os
from collections import deque
from channels.generic.websocket import WebsocketConsumer
from pydub import AudioSegment

# Import your ML tools!
from .video_pipeline import video_model, extract_face, SEQUENCE_LENGTH
from .audio_pipeline import audio_model, preprocess_audio_for_inference

class VideoStreamConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        print("🟢 WebSocket Connected! Dual-Stream Ready.")
        self.frame_buffer = deque(maxlen=SEQUENCE_LENGTH)
        self.frame_count = 0

    def disconnect(self, close_code):
        print("🔴 WebSocket Disconnected.")
        self.frame_buffer.clear()

    def receive(self, text_data):
        data = json.loads(text_data)

        # --- AUDIO PROCESSING ROUTE ---
        if 'audio' in data:
            if 'audio' in data:
                print("🔊 Backend: Received an audio chunk from React!") # 👈 ADD THIS
            
            if audio_model is None:
                print("❌ Backend: Dropped audio because audio_model is None!") # 👈 ADD THIS
                return

            try:
                # 1. Decode the WebM audio blob from React
                audio_data = data['audio'].split(',')[1]
                audio_bytes = base64.b64decode(audio_data)
                
                # 2. Save it to a fast temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_webm:
                    temp_webm.write(audio_bytes)
                    webm_path = temp_webm.name
                
                wav_path = webm_path.replace('.webm', '.wav')
                
                # 3. Convert WebM to standard 16kHz, 16-bit, Mono WAV for our model
                audio_segment = AudioSegment.from_file(webm_path)
                audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2) # 👈 THIS FORCES 16-BIT!
                audio_segment.export(wav_path, format="wav")
                
                # 4. Run native TensorFlow inference
                processed_tensor = preprocess_audio_for_inference(wav_path)
                input_data = tf.expand_dims(processed_tensor, axis=0)
                
                prediction = audio_model.predict(input_data, verbose=0)
                score = float(prediction[0][0])
                label = "FAKE" if score > 0.5 else "REAL"
                
                # 5. Send Audio Result Back
                self.send(text_data=json.dumps({
                    "type": "audio_result",
                    "status": label,
                    "confidence": round((score if score > 0.5 else 1.0 - score) * 100, 2)
                }))
                
                # Cleanup
                os.remove(webm_path)
                os.remove(wav_path)
                
            except Exception as e:
                print(f"❌ Audio Processing Error: {e}")

        # --- VIDEO PROCESSING ROUTE (Your existing code) ---
        elif 'image' in data:
            if video_model is None:
                return

            try:
                image_data = data['image'].split(',')[1]
                image_bytes = base64.b64decode(image_data)
                np_arr = np.frombuffer(image_bytes, np.uint8)
                img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                processed_face = extract_face(img_rgb)
                processed_face = (processed_face / 255.0).astype(np.float32)
                
                self.frame_buffer.append(processed_face)
                self.frame_count += 1

                if len(self.frame_buffer) == SEQUENCE_LENGTH and self.frame_count % 3 == 0:
                    input_data = np.expand_dims(np.array(self.frame_buffer), axis=0)
                    prediction = video_model.predict(input_data, verbose=0)
                    score = float(prediction[0][0])
                    label = "REAL" if score > 0.5 else "FAKE"
                    
                    self.send(text_data=json.dumps({
                        "type": "video_result",
                        "status": label,
                        "confidence": round((score if score > 0.5 else 1.0 - score) * 100, 2)
                    }))
            except Exception as e:
                pass # Ignore dropped frames