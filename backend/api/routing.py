from django.urls import path
from .consumers import VideoStreamConsumer

websocket_urlpatterns = [
    # The URL React will connect to: ws://127.0.0.1:8000/ws/live-stream/
    path('ws/live-stream/', VideoStreamConsumer.as_asgi()),
]