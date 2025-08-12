from rest_framework import serializers
from .models import Interview
from positions.models import NowCoderPosition
from users.models import Resume
import requests
import json

class InterviewCreateSerializer(serializers.ModelSerializer):
    job_position_id = serializers.IntegerField(required=False, allow_null=True)
    resume_id = serializers.IntegerField(required=True)  # 添加必需的简历ID字段
    interview_time = serializers.DateTimeField(
        required=False,
        input_formats=['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ', 'iso-8601'],
        default_timezone=None  # 保持原始时区信息
    )

    class Meta:
        model = Interview
        fields = [
            'id',  # 添加id字段
            'job_position_id',
            'resume_id',  # 添加resume_id字段
            'interview_time',
            'position_name',
            'company_name',
            'position_description',
            'position_requirements',
            'position_type',
            'question_queue',  # 添加问题队列字段
        ]
        read_only_fields = ['id', 'question_queue']  # 标记为只读字段

    def validate_job_position_id(self, value):
        if value:
            try:
                NowCoderPosition.objects.get(id=value)
            except NowCoderPosition.DoesNotExist:
                raise serializers.ValidationError("指定的岗位不存在")
        return value

    def validate_resume_id(self, value):
        """验证简历ID"""
        user = self.context['request'].user
        try:
            resume = Resume.objects.get(id=value, user=user)
            return value
        except Resume.DoesNotExist:
            raise serializers.ValidationError("指定的简历不存在或不属于当前用户")

    def _generate_interview_questions(self, interview):
        """调用个性化推荐API生成面试问题"""
        try:
            from knowledge_base.services import KnowledgeBaseService
            
            # 使用KnowledgeBaseService生成问题
            kb_service = KnowledgeBaseService()
            questions = kb_service.search_relevant_questions(
                position_type=interview.position_type,
                resume=interview.resume,
                limit=8  # 增加问题数量
            )
            
            return questions
            
        except Exception as e:
            print(f"生成面试问题失败: {e}")
            # 返回默认问题
            return [
                '请简单自我介绍一下。',
                f'你为什么选择{interview.company_name}？',
                '请介绍一下你最近的一个项目。',
                '你遇到过最大的技术难题是什么？',
                '你对未来的职业规划是什么？',
                f'你对{interview.position_name}这个岗位有什么了解？',
                '你的优势和劣势分别是什么？',
                '你还有什么问题要问我们的吗？'
            ]

    def create(self, validated_data):
        user = self.context['request'].user
        job_position_id = validated_data.pop('job_position_id', None)
        resume_id = validated_data.pop('resume_id')
        
        # 获取简历对象
        resume = Resume.objects.get(id=resume_id, user=user)
        validated_data['resume'] = resume
        
        # 如果提供了job_position_id，从nowcoder_data表获取相关信息
        if job_position_id:
            nowcoder_position = NowCoderPosition.objects.get(id=job_position_id)
            validated_data['nowcoder_position_id'] = job_position_id  # 存储ID而不是对象
            # 如果没有提供某些字段，则使用nowcoder_position中的信息
            validated_data.setdefault('position_name', nowcoder_position.job_name)
            validated_data.setdefault('company_name', nowcoder_position.company)
            validated_data.setdefault('position_description', nowcoder_position.introduction or nowcoder_position.job_name)
            validated_data.setdefault('position_requirements', nowcoder_position.job_request or '')
            validated_data.setdefault('position_type', nowcoder_position.position_type)
        
        # 设置用户
        validated_data['user'] = user
        
        # 处理面试时间：将前端发送的时间视为本地时间
        if 'interview_time' in validated_data:
            from django.utils import timezone
            import pytz
            
            # 获取前端发送的时间
            frontend_time = validated_data['interview_time']
            
            # 如果前端发送的是时间字符串，直接解析为本地时间
            if isinstance(frontend_time, str):
                # 如果字符串以Z结尾，移除Z
                if frontend_time.endswith('Z'):
                    frontend_time = frontend_time[:-1]
                
                # 解析为datetime对象（无时区信息）
                parsed_time = timezone.datetime.fromisoformat(frontend_time)
                
                # 添加北京时间时区信息
                beijing_tz = pytz.timezone('Asia/Shanghai')
                validated_data['interview_time'] = beijing_tz.localize(parsed_time)
            else:
                # 如果已经是datetime对象，添加本地时区信息
                if frontend_time.tzinfo is None:
                    beijing_tz = pytz.timezone('Asia/Shanghai')
                    validated_data['interview_time'] = beijing_tz.localize(frontend_time)
        else:
            # 如果没有提供面试时间，使用当前本地时间
            from django.utils import timezone
            import pytz
            beijing_tz = pytz.timezone('Asia/Shanghai')
            validated_data['interview_time'] = beijing_tz.localize(timezone.datetime.now())
        
        # 创建面试记录
        interview = super().create(validated_data)
        
        # 生成个性化面试问题队列
        questions = self._generate_interview_questions(interview)
        interview.question_queue = questions
        interview.save()
        
        return interview


class InterviewListSerializer(serializers.ModelSerializer):
    """面试列表序列化器"""
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Interview
        fields = [
            'id',
            'interview_time',
            'position_name',
            'company_name',
            'position_type',
            'question_count',  # 添加问题数量字段
            'created_at',
            'updated_at',
        ]
    
    def to_representation(self, instance):
        """自定义序列化，直接返回北京时间格式"""
        data = super().to_representation(instance)
        
        # 直接返回北京时间格式，不需要转换
        import pytz
        beijing_tz = pytz.timezone('Asia/Shanghai')
        
        # 处理interview_time
        if instance.interview_time:
            # 直接格式化为北京时间
            data['interview_time'] = instance.interview_time.strftime('%Y-%m-%dT%H:%M:%S+08:00')
        
        # 处理created_at
        if instance.created_at:
            # 直接格式化为北京时间
            data['created_at'] = instance.created_at.strftime('%Y-%m-%dT%H:%M:%S+08:00')
        
        # 处理updated_at
        if instance.updated_at:
            # 直接格式化为北京时间
            data['updated_at'] = instance.updated_at.strftime('%Y-%m-%dT%H:%M:%S+08:00')
        
        return data
    
    def get_question_count(self, obj):
        """获取问题数量"""
        return len(obj.question_queue) if obj.question_queue else 0 