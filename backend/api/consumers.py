import json
import base64
import cv2
import numpy as np
from collections import deque
from channels.generic.websocket import WebsocketConsumer

# Import your existing ML tools from the video pipeline!
from .video_pipeline import video_model, extract_face, SEQUENCE_LENGTH, FRAME_SIZE

class VideoStreamConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        print("🟢 WebSocket Connected! Ready for Live Stream.")
        
        # Initialize the rolling buffer (max 20 frames)
        self.frame_buffer = deque(maxlen=SEQUENCE_LENGTH)
        self.frame_count = 0

    def disconnect(self, close_code):
        print("🔴 WebSocket Disconnected.")
        self.frame_buffer.clear()

    def receive(self, text_data):
        if video_model is None:
            self.send(text_data=json.dumps({"error": "Model not loaded on server."}))
            return

        try:
            # 1. Catch the Base64 image from React
            data = json.loads(text_data)
            image_data = data.get('image', '').split(',')[1] # Remove the "data:image/jpeg;base64," header
            
            # 2. Decode back into an OpenCV Image
            image_bytes = base64.b64decode(image_data)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            # 3. Extract the face and normalize (exactly like video_pipeline.py)
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            processed_face = extract_face(img_rgb)
            processed_face = (processed_face / 255.0).astype(np.float32)
            
            # 4. Add to the rolling buffer
            self.frame_buffer.append(processed_face)
            self.frame_count += 1

            # 5. Only predict if the buffer is full (has exactly 20 frames)
            if len(self.frame_buffer) == SEQUENCE_LENGTH:
                # We don't need to predict on EVERY single frame, that will lag the server.
                # Let's predict every 3rd frame once the buffer is full.
                if self.frame_count % 3 == 0:
                    input_data = np.expand_dims(np.array(self.frame_buffer), axis=0)
                    
                    prediction = video_model.predict(input_data, verbose=0)
                    score = float(prediction[0][0])
                    
                    label = "REAL" if score > 0.5 else "FAKE"
                    confidence = score if score > 0.5 else (1.0 - score)

                    # 6. Send the result back to the React frontend
                    self.send(text_data=json.dumps({
                        "status": label,
                        "confidence": round(confidence * 100, 2)
                    }))

        except Exception as e:
            print(f"❌ Error processing live frame: {e}")