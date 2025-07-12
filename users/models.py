from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class User(AbstractUser):
    """用户模型"""
    # 基本信息
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='手机号')
    avatar = models.URLField(blank=True, null=True, verbose_name='头像')
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

class Resume(models.Model):
    """简历模型"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='resume', verbose_name='用户')
    name = models.CharField(max_length=50, verbose_name='姓名')
    age = models.IntegerField(verbose_name='年龄')
    graduation_date = models.DateField(verbose_name='毕业时间')
    education_level = models.CharField(max_length=50, verbose_name='学历')
    expected_position = models.CharField(max_length=100, verbose_name='期望职位')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '简历'
        verbose_name_plural = '简历'

class WorkExperience(models.Model):
    """工作/实习经历"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='work_experiences', verbose_name='简历')
    start_date = models.DateField(verbose_name='开始时间')
    end_date = models.DateField(blank=True, null=True, verbose_name='结束时间')
    company_name = models.CharField(max_length=100, verbose_name='公司名称')
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name='所属部门')
    position = models.CharField(max_length=100, blank=True, null=True, verbose_name='职位名称')
    work_content = models.TextField(verbose_name='工作内容')
    is_internship = models.BooleanField(default=False, verbose_name='是否是实习')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '工作经历'
        verbose_name_plural = '工作经历'
        ordering = ['-start_date']

class ProjectExperience(models.Model):
    """项目经历"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='project_experiences', verbose_name='简历')
    start_date = models.DateField(verbose_name='开始时间')
    end_date = models.DateField(blank=True, null=True, verbose_name='结束时间')
    project_name = models.CharField(max_length=100, verbose_name='项目名称')
    project_role = models.CharField(max_length=100, verbose_name='项目角色')
    project_link = models.URLField(blank=True, null=True, verbose_name='项目链接')
    project_content = models.TextField(verbose_name='项目内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '项目经历'
        verbose_name_plural = '项目经历'
        ordering = ['-start_date']

class EducationExperience(models.Model):
    """教育经历"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='education_experiences', verbose_name='简历')
    start_date = models.DateField(verbose_name='开始时间')
    end_date = models.DateField(blank=True, null=True, verbose_name='结束时间')
    school_name = models.CharField(max_length=100, verbose_name='学校名称')
    education_level = models.CharField(max_length=50, verbose_name='学历')
    major = models.CharField(max_length=100, blank=True, null=True, verbose_name='专业')
    school_experience = models.TextField(blank=True, null=True, verbose_name='在校经历')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '教育经历'
        verbose_name_plural = '教育经历'
        ordering = ['-start_date']

class CustomSection(models.Model):
    """自定义部分（如社团经历等）"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='custom_sections', verbose_name='简历')
    title = models.CharField(max_length=100, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '自定义部分'
        verbose_name_plural = '自定义部分'
        ordering = ['created_at']
