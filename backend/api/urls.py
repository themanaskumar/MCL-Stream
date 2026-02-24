from django.urls import path
from .views import ImageAnalysisView, VideoDetectionView

urlpatterns = [
    path('analyze-image/', ImageAnalysisView.as_view(), name='analyze-image'),
    
    # Add the new video analysis endpoint here
    path('analyze-video/', VideoDetectionView.as_view(), name='analyze-video'),
]