from rest_framework import serializers
from .models import Interview
from knowledge_base.models import JobPosition

class InterviewCreateSerializer(serializers.ModelSerializer):
    job_position_id = serializers.IntegerField(required=False, allow_null=True)
    interview_time = serializers.DateTimeField(required=False)

    class Meta:
        model = Interview
        fields = [
            'id',  # 添加id字段
            'job_position_id',
            'interview_time',
            'position_name',
            'company_name',
            'position_description',
            'position_requirements',
            'position_type',
        ]
        read_only_fields = ['id']  # 标记id为只读字段

    def validate_job_position_id(self, value):
        if value:
            try:
                JobPosition.objects.get(id=value)
            except JobPosition.DoesNotExist:
                raise serializers.ValidationError("指定的岗位不存在")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        job_position_id = validated_data.pop('job_position_id', None)
        
        # 如果提供了job_position_id，从数据库获取相关信息
        if job_position_id:
            job_position = JobPosition.objects.get(id=job_position_id)
            validated_data['job_position'] = job_position
            # 如果没有提供某些字段，则使用job_position中的信息
            validated_data.setdefault('position_name', job_position.name)
            validated_data.setdefault('company_name', job_position.company_name)
            validated_data.setdefault('position_description', job_position.description)
            validated_data.setdefault('position_requirements', job_position.requirements)
            validated_data.setdefault('position_type', job_position.position_type)
        
        # 设置用户
        validated_data['user'] = user
        
        # 如果没有提供面试时间，使用当前时间
        if 'interview_time' not in validated_data:
            from django.utils import timezone
            validated_data['interview_time'] = timezone.now()
        
        return super().create(validated_data) 