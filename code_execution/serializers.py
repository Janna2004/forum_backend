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

    class Meta:
        model = Problem
        fields = [
            'id', 'problem_set', 'problem_set_title', 'category', 'title',
            'description', 'scenario', 'difficulty', 'tags', 'question',
            'reference_answer', 'analysis', 'created_at', 'updated_at'
        ]

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
