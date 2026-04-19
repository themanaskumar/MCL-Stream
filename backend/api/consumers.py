import json
import base64
import cv2
import numpy as np
import io
import tensorflow as tf
from collections import deque
from channels.generic.websocket import WebsocketConsumer
from pydub import AudioSegment
from tensorflow.keras.applications.xception import preprocess_input

# Import your ML tools!
from .video_pipeline import video_model, extract_face, SEQUENCE_LENGTH
from .audio_pipeline import audio_model, preprocess_audio_for_inference

class VideoStreamConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        print("🟢 WebSocket Connected! Dual-Stream Ready.")
        self.frame_buffer = deque(maxlen=SEQUENCE_LENGTH)
        self.frame_count = 0
        self.last_good_face = None 

    def disconnect(self, close_code):
        print("🔴 WebSocket Disconnected.")
        self.frame_buffer.clear()

    def receive(self, text_data):
        data = json.loads(text_data)

        # --- AUDIO PROCESSING ROUTE ---
        if 'audio' in data:
            if audio_model is None:
                return

            try:
                audio_data = data['audio'].split(',')[1]
                audio_bytes = base64.b64decode(audio_data)
                webm_io = io.BytesIO(audio_bytes)
                
                audio_segment = AudioSegment.from_file(webm_io)
                audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                
                wav_io = io.BytesIO()
                audio_segment.export(wav_io, format="wav")
                
                wav_io.seek(0)
                raw_wav_bytes = wav_io.read() 
                
                processed_tensor = preprocess_audio_for_inference(raw_wav_bytes) 
                input_data = tf.expand_dims(processed_tensor, axis=0)
                
                prediction = audio_model.predict(input_data, verbose=0)
                score = float(prediction[0][0])
                
                label = "FAKE" if score > 0.5 else "REAL"
                
                self.send(text_data=json.dumps({
                    "type": "audio_result",
                    "status": label,
                    "confidence": round((score if score > 0.5 else 1.0 - score) * 100, 2)
                }))
                
            except Exception as e:
                print(f"❌ Audio Processing Error: {e}")

        # --- VIDEO PROCESSING ROUTE ---
        elif 'image' in data:
            if video_model is None:
                print("⚠️ [VIDEO DROP] video_model is None! It failed to load in video_pipeline.py.")
                return

            try:
                image_data = data['image'].split(',')[1]
                image_bytes = base64.b64decode(image_data)
                np_arr = np.frombuffer(image_bytes, np.uint8)
                img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                if img_bgr is None:
                    print("⚠️ [VIDEO DROP] OpenCV failed to decode the Base64 frame.")
                    return

                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                
                # Run MediaPipe
                raw_face = extract_face(img_rgb)
                
                if raw_face is not None:
                    # Face found! Format it for Xception and append to buffer
                    processed_face = preprocess_input(raw_face.astype(np.float32))
                    self.frame_buffer.append(processed_face)
                    self.last_good_face = processed_face 
                    self.frame_count += 1
                else:
                    # MediaPipe lost the face
                    if self.last_good_face is not None:
                        # Use the previous valid face to keep the LSTM sequence alive
                        self.frame_buffer.append(self.last_good_face)
                        self.frame_count += 1
                    else:
                        # The stream just started and we haven't found a face yet. Tell the UI!
                        self.send(text_data=json.dumps({
                            "type": "video_result",
                            "status": "NO FACE DETECTED",
                            "confidence": null
                        }))
                        return

                # Send feedback to the UI so you know the frames are arriving and stacking up
                if len(self.frame_buffer) < SEQUENCE_LENGTH:
                    self.send(text_data=json.dumps({
                        "type": "video_result",
                        "status": f"BUFFERING ({len(self.frame_buffer)}/{SEQUENCE_LENGTH})",
                        "confidence": null
                    }))
                    return

                # Predict exactly once per second (every 3rd frame received)
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
                print(f"❌ [VIDEO CRASH] Processing Error: {e}")