from django.urls import re_path
from . import consumers


websocket_urlpatterns = [
    re_path(r'ws/resume/optimize/$', consumers.ResumeOptimizeConsumer.as_asgi()),
]


