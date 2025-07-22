from rest_framework import serializers
from .models import Position, NowCoderPosition

# 原有的Position序列化器 - 保留但不再使用
class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ['id', 'position_name', 'company_name', 'position_url']

# 新的NowCoder职位序列化器
class NowCoderPositionSerializer(serializers.ModelSerializer):
    position_type = serializers.ReadOnlyField()  # 添加计算属性
    
    # 兼容性字段映射
    position_name = serializers.ReadOnlyField()
    company_name = serializers.ReadOnlyField()
    position_url = serializers.ReadOnlyField()
    
    class Meta:
        model = NowCoderPosition
        fields = [
            'id', 'job_name', 'company', 'url', 'salary', 'address', 
            'view_rate', 'ave_speed', 'add_info', 'work_style', 
            'work_time', 'upgrade_chance', 'introduction', 'job_request',
            'position_type',  # 计算字段
            # 兼容性字段
            'position_name', 'company_name', 'position_url'
        ] 