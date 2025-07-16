from django.db import models
from users.models import User, Resume

class JobPosition(models.Model):
    """岗位模型"""
    POSITION_TYPE_CHOICES = [
        ('backend', '后端开发'),
        ('frontend', '前端开发'),
        ('pm', '产品经理'),
        ('qa', '测试'),
        ('algo', '算法'),
    ]
    name = models.CharField(max_length=100, verbose_name='岗位名称')
    company_name = models.CharField(max_length=100, verbose_name='公司名称')
    description = models.TextField(verbose_name='岗位详细信息')
    requirements = models.TextField(blank=True, null=True, verbose_name='岗位要求')
    position_type = models.CharField(max_length=20, choices=POSITION_TYPE_CHOICES, verbose_name='岗位类型', default='backend')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '岗位'
        verbose_name_plural = '岗位'
        ordering = ['-created_at']

class KnowledgeBaseEntry(models.Model):
    """知识库条目"""
    CATEGORY_CHOICES = [
        ('technical', '技术类'),
        ('behavioral', '行为类'),
        ('project', '项目类'),
        ('leadership', '领导力类'),
        ('general', '通用类'),
    ]
    
    question = models.TextField(verbose_name='问题内容')
    answer = models.TextField(verbose_name='标准答案')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='问题类别')
    difficulty_level = models.IntegerField(choices=[(i, f'L{i}') for i in range(1, 6)], verbose_name='难度等级')
    tags = models.JSONField(default=list, verbose_name='标签')
    related_positions = models.ManyToManyField(JobPosition, blank=True, verbose_name='相关岗位')
    company_name = models.CharField(max_length=100, verbose_name='出题公司', default='')
    position_type = models.CharField(max_length=20, choices=JobPosition.POSITION_TYPE_CHOICES, verbose_name='岗位类型', default='backend')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '知识库条目'
        verbose_name_plural = '知识库条目'
        ordering = ['-created_at']

class InterviewQuestion(models.Model):
    """面试问题记录"""
    job_position = models.ForeignKey(JobPosition, on_delete=models.CASCADE, verbose_name='岗位')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, verbose_name='简历')
    questions = models.JSONField(verbose_name='生成的问题列表')
    generation_context = models.TextField(verbose_name='生成上下文')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '面试问题'
        verbose_name_plural = '面试问题'
        ordering = ['-created_at']
