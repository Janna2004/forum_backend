from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .models import Position
from .serializers import PositionSerializer
from django.db.models import Q

# Create your views here.

class PositionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    职位信息视图集
    
    list:
    获取职位列表，支持分页
    
    retrieve:
    获取职位详细信息
    
    search:
    搜索职位，支持职位名称和公司名称搜索
    """
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['position_name', 'company_name']
    ordering_fields = ['id', 'position_name', 'company_name']
    ordering = ['-id']  # 默认按id倒序排序

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        高级搜索接口
        支持职位名称和公司名称的模糊搜索
        """
        keyword = request.query_params.get('keyword', '')
        if not keyword:
            return Response({'error': '请提供搜索关键词'}, status=400)

        queryset = self.get_queryset().filter(
            Q(position_name__icontains=keyword) |
            Q(company_name__icontains=keyword)
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
