import os
import io
from pydub import AudioSegment
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage

# Import your pipelines
from .video_pipeline import analyze_video_pipeline
from .audio_pipeline import analyze_audio
from .ml_handler import analyze_image_pipeline

# --- 1. UPDATED IMAGE VIEW ---
class ImageAnalysisView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        if 'image' not in request.FILES:
            return Response({"error": "No image uploaded"}, status=400)
        
        image_file = request.FILES['image']
        
        image_path = default_storage.save(f"temp/{image_file.name}", image_file)
        full_image_path = os.path.join(default_storage.location, image_path)
        
        try:
            result = analyze_image_pipeline(full_image_path) 
            
            if os.path.exists(full_image_path):
                os.remove(full_image_path)
                
            return Response(result)
        except Exception as e:
            if os.path.exists(full_image_path):
                os.remove(full_image_path)
            return Response({"error": str(e)}, status=500)

# --- 2. VIDEO VIEW (Routes to Dual-Modality logic) ---
class VideoDetectionView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        return upload_video(request)

# --- 3. DUAL-MODALITY VIDEO & AUDIO VIEW (OPTIMIZED) ---
@csrf_exempt
def upload_video(request):
    file_obj = request.FILES.get('video')
    if not file_obj:
         return JsonResponse({"error": "Invalid request or missing video file"}, status=400)
        
    # Save the uploaded video temporarily
    video_path = default_storage.save(f"temp/{file_obj.name}", file_obj)
    full_video_path = os.path.join(default_storage.location, video_path)

    try:
        # 1. Scan the Video Track
        print("🎬 Scanning Video Track...")
        video_result = analyze_video_pipeline(full_video_path)

        # 2. Extract and Scan Audio Track (IN RAM)
        print("🎵 Extracting and Scanning Audio Track (In-Memory)...")
        audio_result = {"status": "NO_AUDIO", "confidence": 0}
        
        try:
            # pydub reads the audio directly out of the video file (mp4, mov, webm, etc.)
            audio_segment = AudioSegment.from_file(full_video_path)
            audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            
            # Export to RAM (BytesIO) instead of the hard drive
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_io.seek(0)
            wav_bytes = wav_io.read()
            
            # Pass the raw RAM bytes directly to your updated pipeline
            audio_result = analyze_audio(wav_bytes)
        except Exception as e:
            print(f"⚠️ Audio extraction skipped (Video might be muted): {e}")

        # 3. The Final Verdict Logic
        overall_status = "REAL"
        if video_result.get('status') == "FAKE" or audio_result.get('status') == "FAKE":
            overall_status = "FAKE"

        # Clean up the single temporary video file
        if os.path.exists(full_video_path): 
            os.remove(full_video_path)

        # Send response
        return JsonResponse({
            "overall_status": overall_status,
            "video": video_result,
            "audio": audio_result
        })

    except Exception as e:
        if os.path.exists(full_video_path): 
            os.remove(full_video_path)
        return JsonResponse({"error": str(e)}, status=500)