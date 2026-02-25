## MCL-Stream

**MCL-Stream** is a full‑stack application for **deepfake detection on images and videos**.  
It combines a Django REST backend (serving ML models) with a React + Vite frontend for an interactive analysis experience.

### Project Structure

- **backend** (Django + DRF)
  - `manage.py` – Django entry point
  - `backend/settings.py` – core settings, CORS, media config
  - `backend/urls.py` – roots `/api/` routes
  - `api/urls.py` – REST endpoints:
    - `POST /api/analyze-image/` – analyze a single image for deepfakes
    - `POST /api/analyze-video/` – analyze a video stream for deepfakes
  - `api/views.py`
    - `ImageAnalysisView` – handles image uploads and calls `analyze_image_pipeline`
    - `VideoDetectionView` – handles video uploads and calls `analyze_video_pipeline`
  - `api/ml_handler.py`
    - Loads a pre‑trained **Xception** image model (`xception_deepfake_image_5o.h5`)
    - Uses MediaPipe `FaceDetector` (`detector.tflite`) to detect faces
    - `analyze_image_pipeline(image_path)`:
      - Reads image in BGR, conditionally detects faces for large images
      - Crops faces (with padding) from the BGR image
      - Runs `predict_single_face` to classify each crop as **REAL** or **FAKE**
      - Falls back to full‑frame analysis if no faces are detected
      - Returns:
        - `status`: `"REAL"` or `"FAKE"`
        - `confidence`: percentage
        - `details`: per‑face results
        - `faces_detected`: count
  - `api/video_pipeline.py`
    - Rebuilds a CNN‑LSTM (Xception + LSTM) architecture and loads weights from `deepfake_video_lstm_v2.keras`
    - Uses the same MediaPipe `FaceDetector`
    - `analyze_video_pipeline(video_path)`:
      - Extracts frames at ~3 FPS using OpenCV
      - For each frame:
        - Detects and crops the most prominent face (with padding)
        - Falls back to center crops if needed
      - Chunks frames into sequences of 20, pads the last chunk if short
      - Runs batch prediction over all chunks and averages scores
      - Returns:
        - `status`: `"REAL"` or `"FAKE"`
        - `confidence`: percentage
        - `raw_score`: average model score
        - `frames_analyzed`, `chunks_processed`
        - `architecture_used`, `note`

- **frontend** (React + Vite)
  - `package.json` – React 19 + React Router 7, Vite configuration
  - `src/main.jsx` – app bootstrap
  - `src/App.jsx` – top‑level routing/layout
  - `src/components/`
    - `Layout.jsx`, `Header.jsx`, `Footer.jsx`
    - `Home.jsx` – overview / landing page
    - `ImageAnalysis.jsx` – UI for uploading and analyzing images
    - `VideoAnalysis.jsx` – UI for uploading and analyzing videos
    - `LiveAnalysis.jsx` – (optional/experimental) live or stream‑like analysis surface
  - `App.css` – global styling

### Backend – Local Setup

- **Prerequisites**
  - Python 3.x
  - Virtualenv (recommended)
  - The ML model files in `backend/api/ml_models/`:
    - `xception_deepfake_image_5o.h5`
    - `deepfake_video_lstm_v2.keras`
    - `detector.tflite`

- **Install & run**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt  # if available, otherwise install Django, djangorestframework, corsheaders, opencv-python, tensorflow/keras, mediapipe, numpy

python manage.py migrate
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`.

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

- **Analyze Video**
  - **Endpoint**: `POST /api/analyze-video/`
  - **Body**: `multipart/form-data` with field `video` (file; e.g. `.mp4`)
  - **Response** (example):

    ```json
    {
      "status": "REAL",
      "confidence": 87.43,
      "raw_score": 0.8743,
      "frames_analyzed": 90,
      "chunks_processed": 5,
      "architecture_used": "CNN-LSTM Hybrid (3 FPS Chunking)",
      "note": "Extracted at 3 FPS. Evaluated 5 sequence(s) of 20 frames."
    }
    ```

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

By default Vite serves at something like `http://localhost:5173/`.  
Make sure the frontend is configured to call the backend API base URL (e.g. `http://127.0.0.1:8000/api/`).

### Typical Workflow

- Start **Django backend** (`python manage.py runserver`)
- Start **React frontend** (`npm run dev` in `frontend`)
- From the UI:
  - Navigate to **Image Analysis** to upload an image and see:
    - Overall prediction (`REAL` / `FAKE`)
    - Confidence and per‑face breakdown when applicable
  - Navigate to **Video Analysis** to upload a video and see:
    - Model verdict over the selected frames and sequences

### Notes & Limitations

- Models are loaded **once at server startup**; first run may take time.
- The app assumes the presence and compatibility of the `.h5`, `.keras`, and `.tflite` model files.
- GPU acceleration and large video handling will depend on your local environment and OpenCV/TensorFlow setup.