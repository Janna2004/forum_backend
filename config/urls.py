"""
URL configuration for config project.

For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path('users/', include('users.urls')),
    path('posts/', include('posts.urls')),
    path('webrtc/', include('webrtc.urls')),
    path('knowledge-base/', include('knowledge_base.urls')),
    path('interviews/', include('interviews.urls')),
    path('positions/', include('positions.urls')),  # 添加positions的URL配置
]
