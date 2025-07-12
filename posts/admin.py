from django.contrib import admin
from .models import Post, Reply

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'updated_at', 'reply_count')
    list_filter = ('created_at', 'author')
    search_fields = ('title', 'content', 'author__username')
    readonly_fields = ('created_at', 'updated_at')
    
    def reply_count(self, obj):
        return obj.replies.count()
    reply_count.short_description = '回复数量'

@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'content_preview', 'parent_reply', 'created_at')
    list_filter = ('created_at', 'author', 'post')
    search_fields = ('content', 'author__username', 'post__title')
    readonly_fields = ('created_at', 'updated_at')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '回复内容预览'
