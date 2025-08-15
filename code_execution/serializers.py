from rest_framework import serializers
from .models import ProblemBank, Problem

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
