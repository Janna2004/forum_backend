import requests
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q
from .models import ProblemBank, Problem
from .serializers import ProblemBankSerializer, ProblemSerializer

logger = logging.getLogger(__name__)

class RunCodeView(APIView):
    def post(self, request):
        try:
            # 验证必需参数
            source_code = request.data.get("source_code")
            language_id = request.data.get("language_id")
            
            if not source_code:
                return Response({"error": "缺少必需参数: source_code"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not language_id:
                return Response({"error": "缺少必需参数: language_id"}, status=status.HTTP_400_BAD_REQUEST)
            
            stdin = request.data.get("stdin", "")

            submission_url = "https://judge0-ce.p.rapidapi.com/submissions"

            headers = {
                "x-rapidapi-host": "judge0-ce.p.rapidapi.com",
                "x-rapidapi-key": "76720345bfmsha48b5d6bd12c910p1a4946jsn87edb9d8e75d",  # 用户提供的RapidAPI密钥
                "content-type": "application/json"
            }

            payload = {
                "source_code": source_code,
                "language_id": language_id,
                "stdin": stdin
            }

            logger.info(f"提交代码执行请求: language_id={language_id}")

            # 创建提交任务
            res = requests.post(submission_url, json=payload, headers=headers, timeout=30)
            res.raise_for_status()  # 检查请求是否成功
            
            response_data = res.json()
            token = response_data.get("token")
            
            if not token:
                logger.error(f"API响应中没有token: {response_data}")
                return Response({"error": "API响应格式错误"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 查询运行结果
            result_url = f"{submission_url}/{token}"
            result_res = requests.get(result_url, headers=headers, timeout=30)
            result_res.raise_for_status()  # 检查请求是否成功
            result = result_res.json()

            logger.info(f"代码执行完成: token={token}")
            return Response(result)
            
        except requests.exceptions.Timeout:
            logger.error("请求超时")
            return Response({"error": "请求超时，请稍后重试"}, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return Response({"error": "请求失败", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            return Response({"error": "发生未知错误", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProblemBankListView(generics.ListAPIView):
    """获取题库列表接口"""
    serializer_class = ProblemBankSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """根据分类过滤题库"""
        category = self.request.query_params.get('category')
        difficulty = self.request.query_params.get('difficulty')
        is_algorithm = self.request.query_params.get('is_algorithm')
        
        queryset = ProblemBank.objects.all()
        
        # 按分类过滤
        if category:
            queryset = queryset.filter(category=category)
        
        # 按难度过滤
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # 按是否为算法题过滤
        if is_algorithm is not None:
            is_algorithm_bool = is_algorithm.lower() == 'true'
            queryset = queryset.filter(is_algorithm=is_algorithm_bool)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'total': queryset.count()
        })

class ProblemListView(generics.ListAPIView):
    """获取题库所有题目详情接口"""
    serializer_class = ProblemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """根据题库ID获取题目"""
        problem_set_id = self.kwargs.get('problem_set_id')
        difficulty = self.request.query_params.get('difficulty')
        tags = self.request.query_params.getlist('tags')
        
        queryset = Problem.objects.filter(problem_set_id=problem_set_id)
        
        # 按难度过滤
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # 按标签过滤
        if tags:
            tag_conditions = Q()
            for tag in tags:
                tag_conditions |= Q(tags__contains=[tag])
            queryset = queryset.filter(tag_conditions)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        problem_set_id = self.kwargs.get('problem_set_id')
        
        # 检查题库是否存在
        try:
            problem_bank = ProblemBank.objects.get(id=problem_set_id)
        except ProblemBank.DoesNotExist:
            return Response({
                'success': False,
                'error': '题库不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'problem_bank': {
                'id': problem_bank.id,
                'title': problem_bank.title,
                'description': problem_bank.description,
                'category': problem_bank.category,
                'difficulty': problem_bank.difficulty,
                'problem_count': problem_bank.real_problem_count,
                'completed_count': 0,
                'completion_rate': 0.0,
                'tags': problem_bank.tags,
                'color': problem_bank.color,
                'is_algorithm': problem_bank.is_algorithm
            },
            'problems': serializer.data,
            'total': queryset.count()
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_problem_detail(request, problem_id):
    """获取单个题目详情"""
    try:
        problem = Problem.objects.get(id=problem_id)
        serializer = ProblemSerializer(problem)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
        
    except Problem.DoesNotExist:
        return Response({
            'success': False,
            'error': '题目不存在'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_categories(request):
    """获取所有分类"""
    categories = ProblemBank.objects.values_list('category', flat=True).distinct()
    
    return Response({
        'success': True,
        'data': list(categories)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_problems(request):
    """关键词搜索题目"""
    keyword = request.query_params.get('keyword', '').strip()
    search_type = request.query_params.get('type', 'all')  # all, bank, problem
    
    if not keyword:
        return Response({
            'success': False,
            'error': '关键词不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    results = {
        'problem_banks': [],
        'problems': []
    }
    
    # 搜索题库
    if search_type in ['all', 'bank']:
        problem_banks = ProblemBank.objects.filter(
            Q(title__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(tags__contains=[keyword])
        )[:10]  # 限制结果数量
        
        for bank in problem_banks:
            results['problem_banks'].append({
                'id': bank.id,
                'title': bank.title,
                'description': bank.description,
                'category': bank.category,
                'difficulty': bank.difficulty,
                'problem_count': bank.real_problem_count,
                'completed_count': 0,
                'completion_rate': 0.0,
                'tags': bank.tags,
                'color': bank.color,
                'is_algorithm': bank.is_algorithm,
                'created_at': bank.created_at,
                'updated_at': bank.updated_at
            })
    
    # 搜索题目
    if search_type in ['all', 'problem']:
        problems = Problem.objects.filter(
            Q(title__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(scenario__icontains=keyword) |
            Q(question__icontains=keyword) |
            Q(tags__contains=[keyword])
        ).select_related('problem_set')[:20]  # 限制结果数量
        
        for problem in problems:
            results['problems'].append({
                'id': problem.id,
                'problem_set': problem.problem_set.id,
                'problem_set_title': problem.problem_set.title,
                'category': problem.category,
                'title': problem.title,
                'description': problem.description,
                'scenario': problem.scenario,
                'difficulty': problem.difficulty,
                'tags': problem.tags,
                'question': problem.question,
                'analysis': problem.analysis,
                'created_at': problem.created_at,
                'updated_at': problem.updated_at
            })
    
    return Response({
        'success': True,
        'data': results,
        'keyword': keyword,
        'total': {
            'problem_banks': len(results['problem_banks']),
            'problems': len(results['problems'])
        }
    })
