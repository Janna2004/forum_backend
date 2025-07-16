from django.urls import path
from . import views

urlpatterns = [
    path('test/', views.test_websocket, name='test_websocket'),
    path('audio-test/', views.audio_ws_test, name='audio_ws_test'),
] 