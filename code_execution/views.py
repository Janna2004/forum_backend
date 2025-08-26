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
from .models import ProblemBank, Problem, ProblemSubmission, ProblemAnswer
from .serializers import ProblemBankSerializer, ProblemSerializer, ProblemSubmissionSerializer, SubmitAnswersSerializer
from .services import ProblemEvaluationService, CodeEvaluationService

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

            logger.info(f"本地代码执行请求: language_id={language_id}, source_code_length={len(source_code)}")

            # 直接使用本地执行
            return self._execute_locally(source_code, language_id, stdin)
            
        except Exception as e:
            logger.error(f"代码执行时发生错误: {str(e)}")
            return Response({
                "error": "代码执行失败", 
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _execute_locally(self, source_code, language_id, stdin):
        """本地执行代码"""
        import subprocess
        import tempfile
        import os
        import time
        
        try:
            # 根据语言ID确定文件扩展名和执行命令
            language_config = {
                71: {"ext": ".py", "cmd": "python", "name": "Python"},  # Python
                63: {"ext": ".js", "cmd": "node", "name": "JavaScript"},  # JavaScript
                54: {"ext": ".cpp", "cmd": "g++", "name": "C++"},  # C++
                50: {"ext": ".c", "cmd": "gcc", "name": "C"},  # C
                62: {"ext": ".java", "cmd": "java", "name": "Java"},  # Java
            }
            
            if language_id not in language_config:
                return Response({
                    "error": "不支持的语言",
                    "details": f"语言ID {language_id} 不支持本地执行"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            config = language_config[language_id]
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix=config["ext"], delete=False, encoding='utf-8') as f:
                f.write(source_code)
                temp_file = f.name
            
            try:
                # 执行代码
                start_time = time.time()
                
                if language_id == 62:  # Java 特殊处理
                    # 编译 Java 文件
                    compile_result = subprocess.run(
                        ["javac", temp_file], 
                        capture_output=True, 
                        text=True, 
                        timeout=10
                    )
                    
                    if compile_result.returncode != 0:
                        return Response({
                            "status": {"id": 4, "description": "Compilation Error"},
                            "stdout": "",
                            "stderr": compile_result.stderr,
                            "time": int((time.time() - start_time) * 1000),
                            "memory": 0
                        })
                    
                    # 执行编译后的类文件
                    class_name = os.path.splitext(os.path.basename(temp_file))[0]
                    class_dir = os.path.dirname(temp_file)
                    
                    result = subprocess.run(
                        [config["cmd"], "-cp", class_dir, class_name],
                        input=stdin,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                else:
                    # 其他语言直接执行
                    result = subprocess.run(
                        [config["cmd"], temp_file],
                        input=stdin,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                
                execution_time = int((time.time() - start_time) * 1000)
                
                # 构建响应（保持与Judge0相同的格式）
                status_id = 3 if result.returncode == 0 else 4
                status_description = "Accepted" if result.returncode == 0 else "Runtime Error"
                
                response_data = {
                    "status": {
                        "id": status_id,
                        "description": status_description
                    },
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "time": execution_time,
                    "memory": 0  # 本地执行无法准确获取内存使用
                }
                
                logger.info(f"本地代码执行成功: {config['name']}, 耗时: {execution_time}ms")
                return Response(response_data)
                
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                    if language_id == 62:  # Java 还需要清理 .class 文件
                        class_file = os.path.splitext(temp_file)[0] + ".class"
                        if os.path.exists(class_file):
                            os.unlink(class_file)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return Response({
                "error": "代码执行超时",
                "details": "本地执行超时（10秒）"
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except Exception as e:
            logger.error(f"本地代码执行失败: {str(e)}")
            return Response({
                "error": "本地代码执行失败",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        
        # 获取题库信息
        try:
            problem_bank = ProblemBank.objects.get(id=problem_set_id)
        except ProblemBank.DoesNotExist:
            return Problem.objects.none()
        
        # 根据题库类型过滤题目
        queryset = Problem.objects.filter(
            problem_set_id=problem_set_id,
            is_algorithm=problem_bank.is_algorithm
        )
        
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
            'total': queryset.count(),
            'filters': {
                'difficulty': request.query_params.get('difficulty'),
                'tags': request.query_params.getlist('tags')
            }
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_answers(request, problem_set_id):
    """提交答题评析接口"""
    try:
        # 验证题库是否存在
        try:
            problem_bank = ProblemBank.objects.get(id=problem_set_id)
        except ProblemBank.DoesNotExist:
            return Response({
                'success': False,
                'error': '题库不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 验证题库是否为非算法题
        if problem_bank.is_algorithm:
            return Response({
                'success': False,
                'error': '该接口仅支持非算法题库'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证请求数据
        serializer = SubmitAnswersSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': '请求数据格式错误',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        answers_data = serializer.validated_data['answers']
        
        # 验证所有题目是否存在且属于该题库
        problem_ids = list(answers_data.keys())
        problems = Problem.objects.filter(id__in=problem_ids, problem_set=problem_bank)
        
        if len(problems) != len(problem_ids):
            return Response({
                'success': False,
                'error': '部分题目不存在或不属于该题库'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建答题提交记录
        submission = ProblemSubmission.objects.create(
            user=request.user,
            problem_bank=problem_bank,
            total_problems=len(problem_ids),
            total_score=0,
            correct_count=0
        )
        
        # 初始化评析服务
        evaluation_service = ProblemEvaluationService()
        
        total_score = 0
        correct_count = 0
        
        # 一次性评析所有题目并生成整体评析 - 只调用一次LLM
        try:
            # 准备评析数据
            problems_and_answers = []
            for problem in problems:
                user_answer = answers_data.get(problem.id, '')
                problems_and_answers.append((problem, user_answer))
            
            # 一次性调用评析服务（包含整体评析）
            result = evaluation_service.evaluate_problems_with_overall_analysis(
                problems_and_answers, 
                problem_bank.title
            )
            
            evaluations = result['evaluations']
            overall_analysis = result['overall_analysis']
            
            # 创建答题记录
            for i, (problem, user_answer) in enumerate(problems_and_answers):
                evaluation = evaluations.get(str(i), {'score': 0, 'analysis': '评析解析失败'})
                
                problem_answer = ProblemAnswer.objects.create(
                    submission=submission,
                    problem=problem,
                    user_answer=user_answer,
                    score=evaluation['score'],
                    max_score=40,  # 满分40分
                    analysis=evaluation['analysis'],
                    strengths="",
                    weaknesses="",
                    suggestions=""
                )
                
                total_score += evaluation['score']
                # 如果得分超过20分（50%）认为是正确
                if evaluation['score'] >= 20:
                    correct_count += 1
            
            # 更新提交记录（包含整体评析）
            submission.total_score = total_score
            submission.correct_count = correct_count
            submission.overall_analysis = overall_analysis
            submission.improvement_suggestions = ""
            submission.save()
                    
        except Exception as e:
            logger.error(f"评析时出错: {str(e)}")
            # 创建默认答题记录
            for problem in problems:
                user_answer = answers_data.get(problem.id, '')
                problem_answer = ProblemAnswer.objects.create(
                    submission=submission,
                    problem=problem,
                    user_answer=user_answer,
                    score=0,
                    max_score=40,
                    analysis="评析服务暂时不可用",
                    strengths="",
                    weaknesses="",
                    suggestions=""
                )
            
            # 更新提交记录（使用默认整体评析）
            submission.total_score = total_score
            submission.correct_count = correct_count
            submission.overall_analysis = "整体表现良好，各题得分较为均衡"
            submission.improvement_suggestions = ""
            submission.save()
        
        # 返回评析结果
        result_serializer = ProblemSubmissionSerializer(submission)
        
        return Response({
            'success': True,
            'message': '答题评析完成',
            'data': result_serializer.data
        })
        
    except Exception as e:
        logger.error(f"答题评析时出错: {str(e)}")
        return Response({
            'success': False,
            'error': '评析过程中发生错误，请稍后重试'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_submission_history(request):
    """获取用户答题历史"""
    try:
        submissions = ProblemSubmission.objects.filter(user=request.user).order_by('-submitted_at')
        serializer = ProblemSubmissionSerializer(submissions, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'total': submissions.count()
        })
        
    except Exception as e:
        logger.error(f"获取答题历史时出错: {str(e)}")
        return Response({
            'success': False,
            'error': '获取答题历史失败'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_submission_detail(request, submission_id):
    """获取答题详情"""
    try:
        submission = ProblemSubmission.objects.get(id=submission_id, user=request.user)
        serializer = ProblemSubmissionSerializer(submission)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
        
    except ProblemSubmission.DoesNotExist:
        return Response({
            'success': False,
            'error': '答题记录不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"获取答题详情时出错: {str(e)}")
        return Response({
            'success': False,
            'error': '获取答题详情失败'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def evaluate_code_answers(request):
    """代码题答案评析接口"""
    try:
        # 验证请求数据
        problem_answers = request.data.get('problem_answers', [])
        if not problem_answers:
            return Response({
                'success': False,
                'error': '缺少必需参数: problem_answers'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证每个答案的格式
        for answer in problem_answers:
            if not isinstance(answer, dict):
                return Response({
                    'success': False,
                    'error': 'problem_answers 格式错误，应为字典列表'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if 'problem_id' not in answer or 'source_code' not in answer:
                return Response({
                    'success': False,
                    'error': '每个答案必须包含 problem_id 和 source_code'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not answer['problem_id'] or not answer['source_code']:
                return Response({
                    'success': False,
                    'error': 'problem_id 和 source_code 不能为空'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # 调用评析服务
        code_evaluation_service = CodeEvaluationService()
        result = code_evaluation_service.evaluate_code_answers(problem_answers)
        
        if result['success']:
            return Response({
                'success': True,
                'data': result['results']
            })
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"代码评析接口出错: {str(e)}")
        return Response({
            'success': False,
            'error': f'评析失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_code_hint(request):
    """代码提示接口"""
    try:
        # 验证请求数据
        problem_id = request.data.get('problem_id', '')
        current_code = request.data.get('current_code', '')
        language = request.data.get('language', 'Python')
        
        if not problem_id:
            return Response({
                'success': False,
                'error': '缺少必需参数: problem_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取题目信息
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return Response({
                'success': False,
                'error': '题目不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 调用代码提示服务
        code_evaluation_service = CodeEvaluationService()
        result = code_evaluation_service.get_code_hint(
            problem, 
            current_code, 
            language
        )
        
        if result['success']:
            return Response({
                'success': True,
                'data': result['data']
            })
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"代码提示接口出错: {str(e)}")
        return Response({
            'success': False,
            'error': f'获取代码提示失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
