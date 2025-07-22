from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .models import Position, NowCoderPosition
from .serializers import PositionSerializer, NowCoderPositionSerializer
from django.db.models import Q

# Create your views here.

# 原有的PositionViewSet - 保留但不再使用
class OldPositionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    原有职位信息视图集（已废弃）
    """
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['position_name', 'company_name']
    ordering_fields = ['id', 'position_name', 'company_name']
    ordering = ['-id']

# 新的职位视图集 - 使用NowCoder数据
class PositionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    牛客网职位信息视图集
    
    list:
    获取职位列表，支持分页、搜索和过滤
    
    retrieve:
    获取职位详细信息
    
    search:
    搜索职位，支持职位名称、公司名称、地址等搜索
    
    filter_by_type:
    根据岗位类型过滤职位
    """
    queryset = NowCoderPosition.objects.all()
    serializer_class = NowCoderPositionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['job_name', 'company', 'address', 'work_style']
    ordering_fields = ['id', 'job_name', 'company']
    ordering = ['-id']  # 默认按id倒序排序

    def get_queryset(self):
        """自定义查询集，支持更多过滤选项"""
        queryset = super().get_queryset()
        
        # 根据薪资过滤
        salary_filter = self.request.query_params.get('salary', None)
        if salary_filter:
            queryset = queryset.filter(salary__icontains=salary_filter)
        
        # 根据工作类型过滤
        work_style = self.request.query_params.get('work_style', None)
        if work_style:
            queryset = queryset.filter(work_style__icontains=work_style)
        
        # 根据地址过滤
        address = self.request.query_params.get('address', None)
        if address:
            queryset = queryset.filter(address__icontains=address)
        
        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        高级搜索接口
        支持职位名称、公司名称、地址、工作类型的模糊搜索
        """
        keyword = request.query_params.get('keyword', '')
        if not keyword:
            return Response({'error': '请提供搜索关键词'}, status=400)

        queryset = self.get_queryset().filter(
            Q(job_name__icontains=keyword) |
            Q(company__icontains=keyword) |
            Q(address__icontains=keyword) |
            Q(work_style__icontains=keyword) |
            Q(introduction__icontains=keyword) |
            Q(job_request__icontains=keyword)
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def filter_by_type(self, request):
        """
        根据岗位类型过滤职位
        可用类型: backend, frontend, pm, qa, algo, data, other
        """
        position_type = request.query_params.get('type', '')
        if not position_type:
            return Response({'error': '请提供岗位类型'}, status=400)

        queryset = self.get_queryset()
        
        # 根据岗位类型关键字过滤
        if position_type == 'backend':
            keywords = ['后端', 'backend', 'java', 'python', 'go', 'nodejs', 'node.js', 'php', 'c++', '服务端', 'api']
        elif position_type == 'frontend':
            keywords = ['前端', 'frontend', 'javascript', 'js', 'react', 'vue', 'angular', 'html', 'css', 'typescript', 'ts']
        elif position_type == 'pm':
            keywords = ['产品', 'product', 'pm', '产品经理', 'product manager', '需求', '运营']
        elif position_type == 'qa':
            keywords = ['测试', 'test', 'qa', 'quality', '自动化测试', '接口测试', '性能测试']
        elif position_type == 'algo':
            keywords = ['算法', 'algorithm', '机器学习', 'ml', '深度学习', 'ai', '人工智能']
        elif position_type == 'data':
            keywords = ['数据', 'data', '大数据', 'bigdata', '数据分析', '数据挖掘', '数据科学', '数据工程']
        else:
            return Response({'error': '无效的岗位类型'}, status=400)

        # 构建查询条件
        q_objects = Q()
        for keyword in keywords:
            q_objects |= Q(job_name__icontains=keyword) | Q(job_request__icontains=keyword) | Q(add_info__icontains=keyword)
        
        queryset = queryset.filter(q_objects)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        获取岗位统计信息
        """
        total_count = self.get_queryset().count()
        
        # 统计各个类型的岗位数量
        type_stats = {}
        type_keywords = {
            'backend': ['后端', 'java', 'python', 'go', 'php', 'c++'],
            'frontend': ['前端', 'javascript', 'react', 'vue', 'angular'],
            'pm': ['产品', 'pm', '产品经理'],
            'qa': ['测试', 'qa', 'quality'],
            'algo': ['算法', '机器学习', 'ai'],
            'data': ['数据', 'bigdata', '数据分析']
        }
        
        for type_name, keywords in type_keywords.items():
            q_objects = Q()
            for keyword in keywords:
                q_objects |= Q(job_name__icontains=keyword)
            count = self.get_queryset().filter(q_objects).count()
            type_stats[type_name] = count
        
        # 统计公司数量
        company_count = self.get_queryset().values('company').distinct().count()
        
        return Response({
            'total_positions': total_count,
            'total_companies': company_count,
            'position_types': type_stats
        })
