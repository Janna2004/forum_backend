from django.db import models
from users.models import User
from knowledge_base.models import JobPosition
import uuid

class Interview(models.Model):
    """面试模型"""
    POSITION_TYPE_CHOICES = JobPosition.POSITION_TYPE_CHOICES

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    
    # 面试时间相关
    interview_time = models.DateTimeField(verbose_name='面试时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    # 岗位相关信息
    job_position = models.ForeignKey(
        JobPosition, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name='关联岗位'
    )
    position_name = models.CharField(max_length=100, verbose_name='岗位名称')
    company_name = models.CharField(max_length=100, blank=True, verbose_name='公司名称')
    position_description = models.TextField(verbose_name='岗位详细信息')
    position_requirements = models.TextField(blank=True, null=True, verbose_name='岗位要求')
    position_type = models.CharField(
        max_length=20, 
        choices=POSITION_TYPE_CHOICES, 
        verbose_name='岗位类型', 
        default='backend'
    )

    class Meta:
        verbose_name = '面试'
        verbose_name_plural = '面试'
        ordering = ['-interview_time']

class InterviewAnswer(models.Model):
    """面试答题记录"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='answers', verbose_name='面试')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interview_answers', verbose_name='用户')
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
