from django.db import models
from django.conf import settings

# Create your models here.

class Tag(models.Model):
    """标签模型"""
    TAG_TYPES = [
        ('company', '公司'),
        ('position', '岗位'),
        ('skill', '技能'),
        ('industry', '行业'),
        ('level', '级别'),
        ('other', '其他'),
    ]
    
    name = models.CharField(max_length=50, verbose_name='标签名称')
    tag_type = models.CharField(max_length=20, choices=TAG_TYPES, default='other', verbose_name='标签类型')
    description = models.TextField(blank=True, null=True, verbose_name='标签描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '标签'
        verbose_name_plural = '标签'
        unique_together = ['name', 'tag_type']  # 确保同类型下标签名称唯一
        ordering = ['tag_type', 'name']
    
    def __str__(self):
        return f"[{self.get_tag_type_display()}] {self.name}"

class Post(models.Model):
    title = models.CharField(max_length=200, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='作者')
    tags = models.ManyToManyField(Tag, blank=True, verbose_name='标签')
    likes_count = models.PositiveIntegerField(default=0, verbose_name='点赞数')
    replies_count = models.PositiveIntegerField(default=0, verbose_name='回复数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '帖子'
        verbose_name_plural = '帖子'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Reply(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='replies', verbose_name='帖子')
    content = models.TextField(verbose_name='回复内容')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='回复者')
    parent_reply = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='child_replies', verbose_name='父回复')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='回复时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '回复'
        verbose_name_plural = '回复'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username} 回复 {self.post.title}"
