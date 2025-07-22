from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Interview
from .serializers import InterviewCreateSerializer, InterviewListSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from .models import CodingProblem, CodingExample
import logging

logger = logging.getLogger(__name__)

# Create your views here.

class InterviewCreateView(generics.CreateAPIView):
    """创建面试接口"""
    queryset = Interview.objects.all()
    serializer_class = InterviewCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # 添加调试日志
        logger.info(f"创建面试请求 - 用户: {request.user.id}")
        logger.info(f"请求数据: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            # 详细记录验证错误
            logger.error(f"面试创建验证失败 - 用户: {request.user.id}")
            logger.error(f"验证错误详情: {serializer.errors}")
            logger.error(f"请求数据: {request.data}")
            
            return Response({
                'errors': serializer.errors,
                'msg': '数据验证失败'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            interview = serializer.save()
            logger.info(f"面试创建成功 - ID: {interview.id}, 用户: {request.user.id}")
            
            return Response({
                'id': interview.id,
                'interview_time': interview.interview_time,
                'position_name': interview.position_name,
                'company_name': interview.company_name,
                'position_type': interview.position_type,
                'question_queue': interview.question_queue,  # 添加问题队列信息
                'question_count': len(interview.question_queue) if interview.question_queue else 0,  # 问题数量
                'msg': '面试创建成功'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"面试创建异常 - 用户: {request.user.id}, 错误: {str(e)}")
            return Response({
                'error': f'创建面试时出错: {str(e)}',
                'msg': '服务器内部错误'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InterviewListView(generics.ListAPIView):
    """获取用户面试列表接口"""
    serializer_class = InterviewListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """只返回当前用户的面试记录"""
        return Interview.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'interviews': serializer.data,
            'total': queryset.count()
        }, status=status.HTTP_200_OK)

class CodingProblemPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_coding_problems(request):
    """获取代码题列表（分页）"""
    # 过滤参数
    difficulty = request.GET.get('difficulty')
    position_type = request.GET.get('position_type')
    tag = request.GET.get('tag')
    
    queryset = CodingProblem.objects.all()
    
    # 应用过滤
    if difficulty:
        queryset = queryset.filter(difficulty=difficulty)
    if position_type:
        queryset = queryset.filter(position_types__contains=[position_type])
    if tag:
        queryset = queryset.filter(tags__contains=[tag])
    
    # 分页
    paginator = CodingProblemPagination()
    problems = paginator.paginate_queryset(queryset, request)
    
    # 序列化
    result = []
    for problem in problems:
        result.append({
            'id': problem.id,
            'number': problem.number,
            'title': problem.title,
            'difficulty': problem.difficulty,
            'tags': problem.tags,
            'companies': problem.companies,
            'position_types': problem.position_types,
            'created_at': problem.created_at,
            'updated_at': problem.updated_at
        })
    
    return paginator.get_paginated_response(result)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_coding_problem_detail(request, problem_id):
    """获取代码题详细信息"""
    problem = get_object_or_404(CodingProblem, id=problem_id)
    examples = CodingExample.objects.filter(problem=problem).order_by('order')
    
    # 序列化
    examples_data = []
    for example in examples:
        examples_data.append({
            'input_data': example.input_data,
            'output_data': example.output_data,
            'explanation': example.explanation,
            'order': example.order
        })
    
    return Response({
        'id': problem.id,
        'number': problem.number,
        'title': problem.title,
        'description': problem.description,
        'difficulty': problem.difficulty,
        'tags': problem.tags,
        'companies': problem.companies,
        'position_types': problem.position_types,
        'examples': examples_data,
        'created_at': problem.created_at,
        'updated_at': problem.updated_at
    })
