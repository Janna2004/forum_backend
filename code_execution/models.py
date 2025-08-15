from django.db import models

class ProblemBank(models.Model):
    """题库列表模型"""
    DIFFICULTY_CHOICES = [
        ('Easy', '简单'),
        ('Medium', '中等'),
        ('Hard', '困难'),
    ]
    
    CATEGORY_CHOICES = [
        ('前端开发', '前端开发'),
        ('后端开发', '后端开发'),
        ('算法设计', '算法设计'),
        ('测试开发', '测试开发'),
        ('产品经理', '产品经理'),
        ('数据分析', '数据分析'),
    ]
    
    id = models.CharField(max_length=50, primary_key=True, verbose_name='题库ID')
    title = models.CharField(max_length=200, verbose_name='题库标题')
    description = models.TextField(verbose_name='题库描述')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name='分类')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, verbose_name='难度')
    problem_count = models.IntegerField(default=0, verbose_name='题目总数')
    completed_count = models.IntegerField(default=0, verbose_name='已完成数量')
    tags = models.JSONField(default=list, verbose_name='标签')
    color = models.CharField(max_length=50, default='bg-purple-300', verbose_name='颜色主题')
    is_algorithm = models.BooleanField(default=False, verbose_name='是否为算法题')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '题库'
        verbose_name_plural = '题库'
        ordering = ['category', 'difficulty', 'title']
    
    def __str__(self):
        return f"{self.category} - {self.title}"
    
    @property
    def completion_rate(self):
        """完成率"""
        if self.problem_count == 0:
            return 0
        return round((self.completed_count / self.problem_count) * 100, 1)
    
    @property
    def real_problem_count(self):
        """获取真实的题目数量"""
        return self.problems.count()

class Problem(models.Model):
    """题目详情模型"""
    DIFFICULTY_CHOICES = [
        ('Easy', '简单'),
        ('Medium', '中等'),
        ('Hard', '困难'),
    ]
    
    CATEGORY_CHOICES = [
        ('前端开发', '前端开发'),
        ('后端开发', '后端开发'),
        ('算法设计', '算法设计'),
        ('测试开发', '测试开发'),
        ('产品经理', '产品经理'),
        ('数据分析', '数据分析'),
    ]
    
    id = models.CharField(max_length=50, primary_key=True, verbose_name='题目ID')
    problem_set = models.ForeignKey(ProblemBank, on_delete=models.CASCADE, related_name='problems', verbose_name='所属题库')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name='分类')
    title = models.CharField(max_length=200, verbose_name='题目标题')
    description = models.TextField(verbose_name='题目描述')
    scenario = models.TextField(verbose_name='场景描述')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, verbose_name='难度')
    tags = models.JSONField(default=list, verbose_name='标签')
    question = models.TextField(verbose_name='问题内容')
    reference_answer = models.TextField(verbose_name='参考答案')
    analysis = models.TextField(verbose_name='题目分析')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '题目'
        verbose_name_plural = '题目'
        ordering = ['problem_set', 'difficulty', 'title']
    
    def __str__(self):
        return f"{self.problem_set.title} - {self.title}"
