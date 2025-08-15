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
    problem_count = models.IntegerField(default=0, verbose_name='题目总数') # This will be updated by management command
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
    is_algorithm = models.BooleanField(default=False, verbose_name='是否为算法题')
    
    # 通用字段
    question = models.TextField(verbose_name='问题内容')
    reference_answer = models.TextField(verbose_name='参考答案')
    analysis = models.TextField(verbose_name='题目分析')
    
    # 算法题特有字段
    algorithm_constraints = models.JSONField(blank=True, null=True, verbose_name='算法题约束条件')
    algorithm_test_cases = models.JSONField(blank=True, null=True, verbose_name='算法题测试用例')
    algorithm_solution = models.TextField(blank=True, null=True, verbose_name='算法题解答')
    algorithm_code_template = models.TextField(blank=True, null=True, verbose_name='算法题代码模板')
    
    # 非算法题特有字段
    non_algorithm_knowledge_points = models.JSONField(blank=True, null=True, verbose_name='非算法题知识点')
    non_algorithm_scoring_criteria = models.JSONField(blank=True, null=True, verbose_name='非算法题评分标准')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '题目'
        verbose_name_plural = '题目'
        ordering = ['problem_set', 'difficulty', 'title']

    def __str__(self):
        return f"{self.problem_set.title} - {self.title}"
    
    @property
    def test_cases(self):
        """获取测试用例（仅算法题）"""
        if self.is_algorithm and self.algorithm_test_cases:
            return self.algorithm_test_cases
        return None
    
    @property
    def constraints(self):
        """获取约束条件（仅算法题）"""
        if self.is_algorithm and self.algorithm_constraints:
            return self.algorithm_constraints
        return None
    
    @property
    def code_template(self):
        """获取代码模板（仅算法题）"""
        if self.is_algorithm and self.algorithm_code_template:
            return self.algorithm_code_template
        return None
    
    @property
    def knowledge_points(self):
        """获取知识点（仅非算法题）"""
        if not self.is_algorithm and self.non_algorithm_knowledge_points:
            return self.non_algorithm_knowledge_points
        return None
    
    @property
    def scoring_criteria(self):
        """获取评分标准（仅非算法题）"""
        if not self.is_algorithm and self.non_algorithm_scoring_criteria:
            return self.non_algorithm_scoring_criteria
        return None

class ProblemSubmission(models.Model):
    """答题提交记录模型"""
    from users.models import User

    id = models.AutoField(primary_key=True, verbose_name='提交ID')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    problem_bank = models.ForeignKey(ProblemBank, on_delete=models.CASCADE, verbose_name='题库')
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')
    total_score = models.FloatField(default=0, verbose_name='总分')
    total_problems = models.IntegerField(default=0, verbose_name='总题数')
    correct_count = models.IntegerField(default=0, verbose_name='正确题数')
    overall_analysis = models.TextField(blank=True, verbose_name='整体评析')
    improvement_suggestions = models.TextField(blank=True, verbose_name='改进建议')

    class Meta:
        verbose_name = '答题提交记录'
        verbose_name_plural = '答题提交记录'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.user.username} - {self.problem_bank.title} - {self.submitted_at}"

class ProblemAnswer(models.Model):
    """单题答题记录模型"""
    submission = models.ForeignKey(ProblemSubmission, on_delete=models.CASCADE, related_name='answers', verbose_name='提交记录')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, verbose_name='题目')
    user_answer = models.TextField(verbose_name='用户答案')
    score = models.FloatField(default=0, verbose_name='得分')
    max_score = models.FloatField(default=10, verbose_name='满分')
    analysis = models.TextField(blank=True, verbose_name='评析')
    strengths = models.TextField(blank=True, verbose_name='优点')
    weaknesses = models.TextField(blank=True, verbose_name='不足')
    suggestions = models.TextField(blank=True, verbose_name='建议')

    class Meta:
        verbose_name = '单题答题记录'
        verbose_name_plural = '单题答题记录'
        ordering = ['submission', 'problem']

    def __str__(self):
        return f"{self.submission.user.username} - {self.problem.title} - {self.score}/{self.max_score}"
