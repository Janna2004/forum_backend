from django.shortcuts import render, get_object_or_404
from django.db.models import Avg
import logging

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination

from .models import Interview, InterviewAnswer, CodingProblem, CodingExample
from .serializers import InterviewCreateSerializer, InterviewListSerializer
from .services import InterviewEvaluationService

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_interview_scores(request, interview_id):
    """获取面试的总体评分"""
    # 获取面试实例，确保是当前用户的面试
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)
    
    # 获取该面试的所有答案
    answers = InterviewAnswer.objects.filter(interview=interview)
    
    if not answers.exists():
        return Response({
            'error': '该面试还没有任何回答记录',
            'msg': '无法计算评分'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 计算每个维度的平均分
    scores = answers.aggregate(
        avg_professional_knowledge=Avg('professional_knowledge'),
        avg_skill_matching=Avg('skill_matching'),
        avg_communication_skills=Avg('communication_skills'),
        avg_logical_thinking=Avg('logical_thinking'),
        avg_innovation_ability=Avg('innovation_ability'),
        avg_stress_handling=Avg('stress_handling')
    )
    
    # 计算总平均分
    total_score = sum([
        scores['avg_professional_knowledge'],
        scores['avg_skill_matching'],
        scores['avg_communication_skills'],
        scores['avg_logical_thinking'],
        scores['avg_innovation_ability'],
        scores['avg_stress_handling']
    ]) / 6.0
    
    # 构建返回数据
    response_data = {
        'interview_id': interview_id,
        'total_answers': answers.count(),
        'scores': {
            'professional_knowledge': round(scores['avg_professional_knowledge'], 2),
            'skill_matching': round(scores['avg_skill_matching'], 2),
            'communication_skills': round(scores['avg_communication_skills'], 2),
            'logical_thinking': round(scores['avg_logical_thinking'], 2),
            'innovation_ability': round(scores['avg_innovation_ability'], 2),
            'stress_handling': round(scores['avg_stress_handling'], 2)
        },
        'total_score': round(total_score, 2)
    }
    
    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_interview_evaluation(request, format=None):
    """获取面试评估结果"""
    try:
        # 获取interview_id参数
        interview_id = request.query_params.get('interview_id')
        if not interview_id or not interview_id.isdigit():
            return Response(
                {'error': '请提供有效的interview_id参数'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 验证面试记录是否属于当前用户
        interview = get_object_or_404(
            Interview,
            id=int(interview_id),
            user=request.user
        )
        
        # 获取评估结果
        evaluation_service = InterviewEvaluationService()
        result = evaluation_service.get_evaluation_result(interview_id)
        
        if not result:
            return Response(
                {'error': '无法生成评估结果，可能是因为没有答题记录'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 添加调试日志
        logger.info(f"生成面试评估结果 - 面试ID: {interview_id}, 用户: {request.user.id}")
        
        return Response(result)
        
    except Interview.DoesNotExist:
        return Response(
            {'error': '面试记录不存在或无权访问'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': f'参数错误: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"生成评估结果失败 - 面试ID: {interview_id}, 错误: {str(e)}")
        return Response(
            {'error': f'获取评估结果失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_evaluation_overview(request):
    """获取用户总体能力评估"""
    try:
        # 获取评估结果
        evaluation_service = InterviewEvaluationService()
        result = evaluation_service.get_user_overall_evaluation(request.user)
        
        if not result:
            return Response(
                {'error': '无法生成评估结果，可能是因为没有面试记录'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 添加调试日志
        logger.info(f"生成用户总体评估结果 - 用户: {request.user.id}")
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"生成用户总体评估失败 - 用户: {request.user.id}, 错误: {str(e)}")
        return Response(
            {'error': f'获取评估结果失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
