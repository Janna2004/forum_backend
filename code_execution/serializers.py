from rest_framework import serializers
from .models import ProblemBank, Problem, ProblemSubmission, ProblemAnswer

class ProblemBankSerializer(serializers.ModelSerializer):
    """题库列表序列化器"""
    completion_rate = serializers.ReadOnlyField()
    problem_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProblemBank
        fields = [
            'id', 'title', 'description', 'category', 'difficulty',
            'problem_count', 'completed_count', 'completion_rate',
            'tags', 'color', 'is_algorithm', 'created_at', 'updated_at'
        ]
    
    def get_problem_count(self, obj):
        """获取真实的题目数量"""
        return obj.real_problem_count
    
    def get_completed_count(self, obj):
        """统一显示完成数量为0"""
        return 0

class ProblemSerializer(serializers.ModelSerializer):
    """题目详情序列化器"""
    problem_set_title = serializers.CharField(source='problem_set.title', read_only=True)
    
    # 算法题特有字段
    test_cases = serializers.SerializerMethodField()
    constraints = serializers.SerializerMethodField()
    code_template = serializers.SerializerMethodField()
    
    # 非算法题特有字段
    knowledge_points = serializers.SerializerMethodField()
    scoring_criteria = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = [
            'id', 'problem_set', 'problem_set_title', 'category', 'title',
            'description', 'scenario', 'difficulty', 'tags', 'is_algorithm',
            'question', 'reference_answer', 'analysis',
            # 算法题特有字段
            'test_cases', 'constraints', 'code_template',
            # 非算法题特有字段
            'knowledge_points', 'scoring_criteria',
            'created_at', 'updated_at'
        ]
    
    def get_test_cases(self, obj):
        """获取测试用例（仅算法题）"""
        return obj.test_cases
    
    def get_constraints(self, obj):
        """获取约束条件（仅算法题）"""
        return obj.constraints
    
    def get_code_template(self, obj):
        """获取代码模板（仅算法题）"""
        return obj.code_template
    
    def get_knowledge_points(self, obj):
        """获取知识点（仅非算法题）"""
        return obj.knowledge_points
    
    def get_scoring_criteria(self, obj):
        """获取评分标准（仅非算法题）"""
        return obj.scoring_criteria

class ProblemAnswerSerializer(serializers.ModelSerializer):
    """单题答题记录序列化器"""
    problem_question = serializers.CharField(source='problem.question', read_only=True)

    class Meta:
        model = ProblemAnswer
        fields = [
            'problem_question', 'user_answer', 'analysis', 'score', 'max_score'
        ]

class ProblemSubmissionSerializer(serializers.ModelSerializer):
    """答题提交记录序列化器"""
    answers = ProblemAnswerSerializer(many=True, read_only=True)
    accuracy_rate = serializers.SerializerMethodField()

    class Meta:
        model = ProblemSubmission
        fields = [
            'total_score', 'total_problems', 'correct_count', 'accuracy_rate',
            'overall_analysis', 'answers'
        ]

    def get_accuracy_rate(self, obj):
        """计算正确率"""
        if obj.total_problems == 0:
            return 0
        return round((obj.correct_count / obj.total_problems) * 100, 1)

class SubmitAnswersSerializer(serializers.Serializer):
    """提交答案序列化器"""
    answers = serializers.DictField(
        child=serializers.CharField(),
        help_text="题目ID到答案的映射，例如: {'problem-001': '用户答案内容'}"
    )
