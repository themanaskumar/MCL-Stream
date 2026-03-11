import os
import numpy as np
import tensorflow as tf
from moviepy import VideoFileClip
from django.conf import settings

# --- 1. CONFIGURATION & MODEL LOADING ---
# Update this path to exactly where you saved your .keras file
AUDIO_MODEL_PATH = os.path.join(settings.BASE_DIR, 'api/ml_models/deepfake_audio_hybrid_v1.keras')

print("⏳ Loading Audio Deepfake Model...")
try:
    audio_model = tf.keras.models.load_model(AUDIO_MODEL_PATH)
    print("✅ Audio Model Loaded Successfully!")
except Exception as e:
    print(f"❌ Error loading audio model: {e}")
    audio_model = None

MAX_PAD_LEN = 200
MAX_SAMPLES = 24000  # 1.5 seconds at 16000 Hz

# --- 2. AUDIO EXTRACTION ---
def extract_audio_from_video(video_path, output_wav_path):
    """
    Extracts the audio track from an .mp4 and saves it as a .wav file.
    Returns True if successful, False if the video has no audio.
    """
    video = None
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            video.close()
            return False # No audio track in this video
        
        # 🛠️ THE FIX: Removed 'verbose' and 'logger' for MoviePy 2.0 compatibility
        video.audio.write_audiofile(output_wav_path, fps=16000, nbytes=2, codec='pcm_s16le')
        
        video.close()
        return True
    
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return False
        
    finally:
        # 🛠️ THE FAILSAFE: Ensures Windows releases the file lock no matter what!
        if video is not None:
            try:
                video.close()
            except:
                pass

# --- 3. PURE TENSORFLOW PREPROCESSING ---
def preprocess_audio_for_inference(wav_path):
    """
    The exact same native TensorFlow logic used during Kaggle training.
    """
    audio_binary = tf.io.read_file(wav_path)
    audio, sample_rate = tf.audio.decode_wav(audio_binary, desired_channels=1)
    audio = tf.squeeze(audio, axis=-1)
    
    audio_length = tf.shape(audio)[0]
    audio = tf.cond(
        audio_length < MAX_SAMPLES,
        lambda: tf.pad(audio, [[0, MAX_SAMPLES - audio_length]]),
        lambda: audio[:MAX_SAMPLES]
    )
    
    stft = tf.signal.stft(audio, frame_length=512, frame_step=118, fft_length=512)
    spectrogram = tf.abs(stft)
    
    num_spectrogram_bins = tf.shape(spectrogram)[-1]
    linear_to_mel_weight_matrix = tf.signal.linear_to_mel_weight_matrix(
        128, num_spectrogram_bins, 16000, 0.0, 8000.0)
    
    mel_spectrogram = tf.tensordot(spectrogram, linear_to_mel_weight_matrix, 1)
    mel_spectrogram.set_shape(spectrogram.shape[:-1].concatenate(linear_to_mel_weight_matrix.shape[-1:]))
    
    mel_spec_db = tf.math.log(mel_spectrogram + 1e-6)
    
    min_val = tf.reduce_min(mel_spec_db)
    max_val = tf.reduce_max(mel_spec_db)
    mel_spec_db = (mel_spec_db - min_val) / (max_val - min_val + 1e-6)
    
    frames = tf.shape(mel_spec_db)[0]
    mel_spec_db = tf.cond(
        frames < MAX_PAD_LEN,
        lambda: tf.pad(mel_spec_db, [[0, MAX_PAD_LEN - frames], [0, 0]]),
        lambda: mel_spec_db[:MAX_PAD_LEN, :]
    )
    mel_spec_db.set_shape((MAX_PAD_LEN, 128))
    
    return mel_spec_db

# --- 4. PREDICTION FUNCTION ---
def analyze_audio(wav_path):
    """
    Takes a .wav file, preprocesses it, and runs it through the Hybrid model.
    """
    if audio_model is None:
        return {"error": "Audio model not loaded"}

    try:
        # 1. Preprocess the audio using TF
        processed_tensor = preprocess_audio_for_inference(wav_path)
        
        # 2. Add the batch dimension: (200, 128) -> (1, 200, 128)
        input_data = tf.expand_dims(processed_tensor, axis=0)
        
        # 3. Predict!
        prediction = audio_model.predict(input_data, verbose=0)
        score = float(prediction[0][0])
        
        # 0 = REAL, 1 = FAKE
        label = "FAKE" if score > 0.5 else "REAL"
        confidence = score if score > 0.5 else (1.0 - score)
        
        return {
            "status": label,
            "confidence": round(confidence * 100, 2)
        }
        
    except Exception as e:
        print(f"Error during audio prediction: {e}")
        return {"error": "Prediction failed"}