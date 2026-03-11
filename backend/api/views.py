import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage

# Import your pipelines
from .video_pipeline import analyze_video_pipeline
from .audio_pipeline import extract_audio_from_video, analyze_audio

# 🛠️ THE FIX: Import from ml_handler and get the exact function name
from .ml_handler import analyze_image_pipeline

# --- 1. UPDATED IMAGE VIEW ---
class ImageAnalysisView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        if 'image' not in request.FILES:
            return Response({"error": "No image uploaded"}, status=400)
        
        image_file = request.FILES['image']
        
        # 🛠️ Save temporarily because ml_handler expects a file path
        image_path = default_storage.save(f"temp/{image_file.name}", image_file)
        full_image_path = os.path.join(default_storage.location, image_path)
        
        try:
            # Pass the path to your actual function
            result = analyze_image_pipeline(full_image_path) 
            
            # Clean up the temp file
            if os.path.exists(full_image_path):
                os.remove(full_image_path)
                
            return Response(result)
        except Exception as e:
            # Emergency clean up if it crashes
            if os.path.exists(full_image_path):
                os.remove(full_image_path)
            return Response({"error": str(e)}, status=500)

# --- 2. RESTORED OLD VIDEO VIEW (Optional, but keeps urls.py happy) ---
class VideoDetectionView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # We will point this to the new dual-modality logic below!
        return upload_video(request)

# --- 3. NEW DUAL-MODALITY VIDEO & AUDIO VIEW ---
@csrf_exempt
def upload_video(request):
    # This handles both standard Django requests and DRF requests
    file_obj = request.FILES.get('video')
    if not file_obj:
         return JsonResponse({"error": "Invalid request or missing video file"}, status=400)
        
    # Save the uploaded .mp4 temporarily
    video_path = default_storage.save(f"temp/{file_obj.name}", file_obj)
    full_video_path = os.path.join(default_storage.location, video_path)
    
    # Define where the extracted .wav file will temporarily live
    full_audio_path = full_video_path.replace('.mp4', '.wav')

    try:
        # Scan the Video Track
        print("🎬 Scanning Video Track...")
        video_result = analyze_video_pipeline(full_video_path)

        # Separate and Scan the Audio Track
        print("🎵 Extracting and Scanning Audio Track...")
        has_audio = extract_audio_from_video(full_video_path, full_audio_path)
        
        if has_audio:
            audio_result = analyze_audio(full_audio_path)
        else:
            audio_result = {"status": "NO_AUDIO", "confidence": 0}

        # The Final Verdict Logic
        overall_status = "REAL"
        if video_result.get('status') == "FAKE" or audio_result.get('status') == "FAKE":
            overall_status = "FAKE"

        # Clean up temporary files
        if os.path.exists(full_video_path): os.remove(full_video_path)
        if os.path.exists(full_audio_path): os.remove(full_audio_path)

        # Send response
        return JsonResponse({
            "overall_status": overall_status,
            "video": video_result,
            "audio": audio_result
        })

    except Exception as e:
        if os.path.exists(full_video_path): os.remove(full_video_path)
        if os.path.exists(full_audio_path): os.remove(full_audio_path)
        return JsonResponse({"error": str(e)}, status=500)