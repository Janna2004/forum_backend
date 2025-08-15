from rest_framework import serializers
from .models import User, Resume, WorkExperience, ProjectExperience, EducationExperience

class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    target_position = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'avatar',
            'target_position_id', 'target_position_name', 'target_company_name',
            'target_salary_min', 'target_salary_max', 'target_position'
        ]

class PersonalizedRecommendationSerializer(serializers.Serializer):
    """个性化推荐序列化器"""
    currentGoal = serializers.DictField()
    recommendedCompanies = serializers.ListField(child=serializers.DictField())
    recommendedTopics = serializers.ListField(child=serializers.DictField())

class ResumeSerializer(serializers.ModelSerializer):
    """简历序列化器"""
    class Meta:
        model = Resume
        fields = [
            'id', 'resume_name', 'name', 'age', 'graduation_date',
            'education_level', 'expected_position', 'completed',
            'created_at', 'updated_at'
        ]

class WorkExperienceSerializer(serializers.ModelSerializer):
    """工作经历序列化器"""
    class Meta:
        model = WorkExperience
        fields = [
            'id', 'start_date', 'end_date', 'company_name', 'department',
            'position', 'work_content', 'is_internship', 'created_at'
        ]

class ProjectExperienceSerializer(serializers.ModelSerializer):
    """项目经历序列化器"""
    class Meta:
        model = ProjectExperience
        fields = [
            'id', 'start_date', 'end_date', 'project_name', 'project_role',
            'project_link', 'project_content', 'created_at'
        ]

class EducationExperienceSerializer(serializers.ModelSerializer):
    """教育经历序列化器"""
    class Meta:
        model = EducationExperience
        fields = [
            'id', 'start_date', 'end_date', 'school_name', 'education_level',
            'major', 'school_experience', 'created_at'
        ]
