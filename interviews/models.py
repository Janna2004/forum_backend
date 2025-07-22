from django.db import models
from users.models import User
from positions.models import NowCoderPosition
import uuid

class Interview(models.Model):
    """面试模型"""
    POSITION_TYPE_CHOICES = [
        ('backend', '后端开发'),
        ('frontend', '前端开发'),
        ('pm', '产品经理'),
        ('qa', '测试'),
        ('algo', '算法'),
        ('data', '数据'),
        ('other', '其他'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interviews', verbose_name='用户')
    
    # 简历关联
    resume = models.ForeignKey(
        'users.Resume', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='interviews',
        verbose_name='关联简历'
    )
    
    # 面试时间相关
    interview_time = models.DateTimeField(verbose_name='面试时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    # 岗位相关信息 - 使用IntegerField存储nowcoder_data的ID，避免外键约束问题
    nowcoder_position_id = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name='牛客网岗位ID'
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
    
    # 面试问题队列
    question_queue = models.JSONField(
        default=list, 
        blank=True, 
        verbose_name='面试问题队列',
        help_text='存储个性化推荐的面试问题列表'
    )

    class Meta:
        verbose_name = '面试'
        verbose_name_plural = '面试'
        ordering = ['-interview_time']

    @property
    def nowcoder_position(self):
        """获取关联的牛客网岗位对象"""
        if self.nowcoder_position_id:
            try:
                return NowCoderPosition.objects.get(id=self.nowcoder_position_id)
            except NowCoderPosition.DoesNotExist:
                return None
        return None
    
    @property
    def job_position(self):
        """兼容性属性，返回nowcoder_position"""
        return self.nowcoder_position

class InterviewAnswer(models.Model):
    """面试答题记录"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='answers', verbose_name='面试')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interview_answers', verbose_name='用户')
    question = models.TextField(verbose_name='问题')
    answer = models.TextField(verbose_name='答案')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='答题时间')
    ai_analysis = models.TextField(blank=True, null=True, verbose_name='AI分析结果')
    confidence_score = models.FloatField(default=0, verbose_name='信心得分')
    fluency_score = models.FloatField(default=0, verbose_name='流畅度得分')

    class Meta:
        verbose_name = '面试答题记录'
        verbose_name_plural = '面试答题记录'
        ordering = ['created_at']

    def __str__(self):
        user_str = getattr(self.user, 'username', str(self.user))
        question_str = str(self.question)[:10] if self.question else ''
        return f"{user_str} - {question_str}..."

class CodingProblem(models.Model):
    """代码题模型"""
    DIFFICULTY_CHOICES = [
        ('easy', '简单'),
        ('medium', '中等'),
        ('hard', '困难'),
    ]
    
    number = models.CharField(max_length=50, unique=True, verbose_name='题目序号')
    title = models.CharField(max_length=200, verbose_name='题目标题')
    description = models.TextField(verbose_name='题目描述')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, verbose_name='难度等级')
    tags = models.JSONField(default=list, verbose_name='题目标签')
    companies = models.JSONField(default=list, verbose_name='出题公司')
    position_types = models.JSONField(default=list, verbose_name='适用岗位类型')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '代码题'
        verbose_name_plural = '代码题'
        ordering = ['number']
    
    def __str__(self):
        return f"{self.number} - {self.title}"


class CodingExample(models.Model):
    """代码题样例模型"""
    problem = models.ForeignKey(CodingProblem, on_delete=models.CASCADE, related_name='examples', verbose_name='代码题')
    input_data = models.TextField(verbose_name='样例输入')
    output_data = models.TextField(verbose_name='样例输出')
    explanation = models.TextField(blank=True, verbose_name='解释说明')
    order = models.IntegerField(default=1, verbose_name='顺序')
    
    class Meta:
        verbose_name = '代码题样例'
        verbose_name_plural = '代码题样例'
        ordering = ['problem', 'order']
    
    def __str__(self):
        return f"{self.problem.number} - 样例{self.order}"


class InterviewCodingAnswer(models.Model):
    """面试代码题答题记录"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='coding_answers', verbose_name='面试')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coding_answers', verbose_name='用户')
    problem = models.ForeignKey(CodingProblem, on_delete=models.CASCADE, verbose_name='代码题')
    code_answer = models.TextField(verbose_name='代码答案')
    language = models.CharField(max_length=50, default='python', verbose_name='编程语言')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='答题时间')
    
    class Meta:
        verbose_name = '面试代码题答题记录'
        verbose_name_plural = '面试代码题答题记录'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.problem.title}"
