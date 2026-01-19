from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .ml_handler import analyze_image_pipeline
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