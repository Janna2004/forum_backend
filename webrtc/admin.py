from django.contrib import admin
from .models import VideoStream, WebRTCConnection, VideoFrame

@admin.register(VideoStream)
class VideoStreamAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_active', 'created_at', 'viewer_count')
    list_filter = ('is_active', 'created_at', 'user')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    def viewer_count(self, obj):
        return obj.connections.filter(connection_state='connected').count()
    viewer_count.short_description = '观看者数量'

@admin.register(WebRTCConnection)
class WebRTCConnectionAdmin(admin.ModelAdmin):
    list_display = ('peer_id', 'video_stream', 'connection_state', 'created_at')
    list_filter = ('connection_state', 'created_at', 'video_stream')
    search_fields = ('peer_id', 'session_id', 'video_stream__title')
    readonly_fields = ('id', 'created_at', 'updated_at')

@admin.register(VideoFrame)
class VideoFrameAdmin(admin.ModelAdmin):
    list_display = ('video_stream', 'frame_type', 'timestamp', 'frame_size')
    list_filter = ('frame_type', 'timestamp', 'video_stream')
    search_fields = ('video_stream__title',)
    readonly_fields = ('id', 'timestamp')
    
    def frame_size(self, obj):
        return f"{len(obj.frame_data)} bytes"
    frame_size.short_description = '帧大小'
