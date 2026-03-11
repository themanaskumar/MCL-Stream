## MCL-Stream

**MCL-Stream** is an enterprise-grade, full‑stack application for **multimodal deepfake detection on images, videos, and live streams**.

It combines an asynchronous Django REST/WebSocket backend (serving multiple ML models) with a React + Vite frontend for an interactive, real-time analysis experience.

### Project Structure

* **backend** (Django + DRF + Channels)

  * `manage.py` – Django entry point
  * `backend/settings.py` – core settings, CORS, media config, ASGI/Channels routing
  * `backend/urls.py` – roots `/api/` routes
  * `api/urls.py` – REST endpoints:
    * `POST /api/analyze-image/` – analyze a single image for deepfakes
    * `POST /api/analyze-video/` – analyze a video file for both visual and audio deepfakes
  * `api/consumers.py` – ASGI WebSocket consumer:
    * `ws://127.0.0.1:8000/ws/live-stream/` – Handles dual-stream (WebM audio chunks + JPEG video frames) for real-time live deepfake tracking.
  * `api/views.py`
    * `ImageAnalysisView` – handles image uploads and calls `analyze_image_pipeline`
    * `upload_video` – handles `.mp4` uploads, splits the audio and video tracks, routes them to their respective pipelines, and returns a unified verdict.
  * `api/ml_handler.py` (Image Pipeline)
    * Loads a pre‑trained **Xception** image model (`xception_deepfake_image_5o.h5`)
    * Uses MediaPipe `FaceDetector` (`detector.tflite`) to detect faces
    * Returns overall status, confidence, and per-face deepfake details.
  * `api/video_pipeline.py` (Video Pipeline)
    * Rebuilds a CNN‑LSTM (Xception + LSTM) architecture and loads weights from `deepfake_video_lstm_v2.keras`
    * Extracts frames at ~3 FPS using OpenCV, chunks them into sequences of 20, and runs batch predictions.
  * `api/audio_pipeline.py` (Audio Pipeline)
    * Loads a 1D-CNN + BiLSTM hybrid model (`deepfake_audio_hybrid_v1.keras`)
    * Uses `moviepy` to extract `.wav` tracks from video files.
    * Processes audio through pure TensorFlow operations (STFT, Mel Spectrograms) to detect AI-cloned voices.

* **frontend** (React + Vite)

  * `package.json` – React 19, React Router 7, Recharts, Vite configuration
  * `src/main.jsx` – app bootstrap
  * `src/App.jsx` – top‑level routing/layout
  * `src/components/`
    * `Layout.jsx`, `Header.jsx`, `Footer.jsx`
    * `Home.jsx` – overview / landing page
    * `ImageAnalysis.jsx` – UI for uploading and analyzing images
    * `VideoAnalysis.jsx` – UI for uploading and analyzing `.mp4` files (displays dual-modality results)
    * `LiveAnalysis.jsx` – Real-time analysis dashboard using WebSockets. Captures screen share frames via `<canvas>`, chunks system audio via `MediaRecorder`, and plots live deepfake probabilities using a `Recharts` graph.
  * `App.css` – global styling (dark mode, glass-effect UI)

### Backend – Local Setup

* **System Prerequisites**

  * Python 3.x
  * **FFmpeg** (Required for `pydub` audio processing)
    * *Windows:* Run `winget install -e --id Gyan.FFmpeg` in PowerShell as Administrator, then completely restart your terminal/IDE.
    * *Linux/Mac:* `sudo apt install ffmpeg` or `brew install ffmpeg`

* **ML Prerequisites**

  * The ML model files must be placed in `backend/api/ml_models/` (or the root directory as configured):
    * `xception_deepfake_image_5o.h5`
    * `deepfake_video_lstm_v2.keras`
    * `deepfake_audio_hybrid_v1.keras`
    * `detector.tflite`

* **Install & run**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt  

python manage.py migrate
python manage.py runserver
```

The REST API will be available at `http://127.0.0.1:8000/api/` and the WebSocket at `ws://127.0.0.1:8000/ws/live-stream/`.

### API Overview

- **Analyze Image**
  - **Endpoint**: `POST /api/analyze-image/`
  - **Body**: `multipart/form-data` with field `image` (file)
  - **Response** (example):

    ```json
    {
      "status": "FAKE",
      "confidence": 92.15,
      "details": [
        {
          "label": "FAKE",
          "confidence": 0.9215,
          "raw_score": 0.9215,
          "face_index": 1
        }
      ],
      "faces_detected": 1
    }
    ```

- **Analyze Video (Dual-Modality)**
  - **Endpoint**: `POST /api/analyze-video/`
  - **Body**: `multipart/form-data` with field `video` (file; e.g. `.mp4`)
  - **Response** (example):

    ```json
    {
      "overall_status": "FAKE",
      "video": {
        "status": "REAL",
        "confidence": 87.43,
        "raw_score": 0.8743,
        "frames_analyzed": 90,
        "chunks_processed": 5,
        "architecture_used": "CNN-LSTM Hybrid (3 FPS Chunking)",
        "note": "Extracted at 3 FPS. Evaluated 5 sequence(s) of 20 frames."
      },
      "audio": {
        "status": "FAKE",
        "confidence": 98.12
      }
    }
    ```

- **Live Stream Analysis (WebSocket)**
  - **Endpoint**: `ws://127.0.0.1:8000/ws/live-stream/`
  - **Payloads Accepted**:
    - `{"image": "data:image/jpeg;base64,..."}` (Fired at 3 FPS)
    - `{"audio": "data:audio/webm;base64,..."}` (Fired every 1.5 seconds)
  - **Responses**:
    - `{"type": "video_result", "status": "REAL", "confidence": 95.0}`
    - `{"type": "audio_result", "status": "FAKE", "confidence": 99.1}`

### Frontend – Local Setup

- **Prerequisites**
  - Node.js (LTS recommended)
  - npm or pnpm

- **Install & run**

```bash
cd frontend
npm install
npm run dev
```

By default, Vite serves at `http://localhost:5173/`. 

### Typical Workflow

- Start **Django backend** (`python manage.py runserver`)
- Start **React frontend** (`npm run dev` in `frontend`)
- From the UI:
  - Navigate to **Image Analysis** to upload an image and see face-by-face deepfake detection.
  - Navigate to **Video Analysis** to upload an `.mp4` and receive a split verdict on both visual integrity and audio authenticity.
  - Navigate to **Live Analysis** to share a browser tab. The system will process system audio and video frames in real-time, plotting anomalies on a live-scrolling Recharts dashboard.

### Notes & Limitations

- Models are loaded **once at server startup** into global memory; the first run/server boot may take a few seconds.
- Live Analysis requires the user to explicitly grant **"Share tab audio"** permissions in the browser's screen-sharing prompt.
- GPU acceleration and large video handling will depend on your local environment, OpenCV, and TensorFlow setup.