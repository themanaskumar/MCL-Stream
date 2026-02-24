from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .ml_handler import analyze_image_pipeline
from rest_framework import status
import tempfile
import os

class ImageAnalysisView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('image')
        
        if not file_obj:
            return Response({"error": "No image provided"}, status=400)

        # 1. Save file temporarily
        file_path = default_storage.save(f"temp/{file_obj.name}", ContentFile(file_obj.read()))
        full_file_path = os.path.join(default_storage.location, file_path)

        try:
            # 2. Run Analysis
            result = analyze_image_pipeline(full_file_path)
            
            # 3. Clean up (delete temp file)
            if os.path.exists(full_file_path):
                os.remove(full_file_path)

            return Response(result)

        except Exception as e:
            # Cleanup on error
            if os.path.exists(full_file_path):
                os.remove(full_file_path)
            return Response({"error": str(e)}, status=500)

# Video detection pipeline

# Import your brand new video pipeline
from .video_pipeline import analyze_video_pipeline

class VideoDetectionView(APIView):
    def post(self, request, *args, **kwargs):
        # 1. Check if a video was actually sent in the request
        if 'video' not in request.FILES:
            return Response(
                {"error": "No video file provided in the request."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        video_file = request.FILES['video']
        temp_video_path = None

        try:
            # 2. Save the uploaded file temporarily to the server's disk
            # We add a .mp4 suffix so OpenCV knows how to read the codec
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
                for chunk in video_file.chunks():
                    temp_video.write(chunk)
                temp_video_path = temp_video.name

            # 3. Pass the file path to our CNN-LSTM pipeline
            print(f"🎬 Processing video: {video_file.name}...")
            result = analyze_video_pipeline(temp_video_path)

            # 4. Handle any internal pipeline errors
            if "error" in result:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 5. Return the successful prediction to the frontend
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"❌ Server Error during video processing: {e}")
            return Response(
                {"error": "An error occurred while processing the video on the server."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        finally:
            # 6. CRITICAL: Always delete the temporary video to prevent memory leaks
            if temp_video_path and os.path.exists(temp_video_path):
                os.remove(temp_video_path)
                print("🗑️ Temporary video file cleaned up.")