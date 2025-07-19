from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()  # type: ignore

class VideoStream(models.Model):  # type: ignore
    """视频流模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_streams')  # type: ignore
    title = models.CharField(max_length=200, verbose_name='流标题')
    description = models.TextField(blank=True, verbose_name='流描述')
    is_active = models.BooleanField(default=False, verbose_name='是否活跃')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '视频流'
        verbose_name_plural = '视频流'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"

class WebRTCConnection(models.Model):  # type: ignore
    """WebRTC连接模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video_stream = models.ForeignKey(VideoStream, on_delete=models.CASCADE, related_name='connections')  # type: ignore
    session_id = models.CharField(max_length=100, unique=True, verbose_name='会话ID')
    peer_id = models.CharField(max_length=100, verbose_name='对等端ID')
    connection_state = models.CharField(
        max_length=20,
        choices=[
            ('new', '新建'),
            ('connecting', '连接中'),
            ('connected', '已连接'),
            ('disconnected', '已断开'),
            ('failed', '连接失败'),
        ],
        default='new',
        verbose_name='连接状态'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'WebRTC连接'
        verbose_name_plural = 'WebRTC连接'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.peer_id} - {self.connection_state}"

class VideoFrame(models.Model):  # type: ignore
    """视频帧模型（用于存储关键帧）"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video_stream = models.ForeignKey(VideoStream, on_delete=models.CASCADE, related_name='frames')  # type: ignore
    frame_data = models.BinaryField(verbose_name='帧数据')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='时间戳')
    frame_type = models.CharField(
        max_length=20,
        choices=[
            ('keyframe', '关键帧'),
            ('interframe', '中间帧'),
        ],
        default='keyframe',
        verbose_name='帧类型'
    )
    
    class Meta:
        verbose_name = '视频帧'
        verbose_name_plural = '视频帧'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.video_stream.title} - {self.timestamp}"

class InterviewAnswer(models.Model):  # type: ignore
    """面试答题记录"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video_stream = models.ForeignKey(VideoStream, on_delete=models.CASCADE, related_name='answers', verbose_name='面试流')  # type: ignore
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interview_answers', verbose_name='用户')  # type: ignore
    question = models.TextField(verbose_name='问题')
    answer = models.TextField(verbose_name='答案')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='答题时间')

    class Meta:
        verbose_name = '面试答题记录'
        verbose_name_plural = '面试答题记录'
        ordering = ['created_at']

    def __str__(self):
        user_str = getattr(self.user, 'username', str(self.user))
        question_str = str(self.question)[:10] if self.question else ''
        return f"{user_str} - {question_str}..."
