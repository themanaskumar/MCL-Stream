from django.urls import path
from .views import ImageAnalysisView

urlpatterns = [
    path('analyze-image/', ImageAnalysisView.as_view(), name='analyze-image'),
]