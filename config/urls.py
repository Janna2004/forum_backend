"""
URL configuration for config project.

For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('users.urls')),
    path('', include('posts.urls')),
    path('', include('webrtc.urls')),
    path('', include('knowledge_base.urls')),
    path('', include('interviews.urls')),
    path('', include('positions.urls')),  # 添加positions的URL配置
]
