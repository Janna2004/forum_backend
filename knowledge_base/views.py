from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
import json
from users.models import Resume
from .models import JobPosition
from .services import KnowledgeBaseService

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def generate_interview_questions(request):
    """生成面试问题API"""
    try:
        data = json.loads(request.body)
        
        # 验证必需字段
        required_fields = ['job_name', 'company_name', 'job_description', 'resume_id']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'error': f'缺少必需字段: {field}'
                }, status=400)
        
        # 获取或创建岗位
        job_position, created = JobPosition.objects.get_or_create(
            name=data['job_name'],
            company_name=data['company_name'],
            defaults={
                'description': data['job_description'],
                'requirements': data.get('job_requirements', '')
            }
        )
        
        # 获取简历
        resume = get_object_or_404(Resume, id=data['resume_id'])
        
        # 检查权限（只能访问自己的简历）
        if resume.user != request.user:
            return JsonResponse({
                'success': False,
                'error': '无权访问此简历'
            }, status=403)
        
        # 生成面试问题
        service = KnowledgeBaseService()
        questions = service.search_relevant_questions(
            job_position=job_position,
            resume=resume,
            limit=data.get('limit', 5)
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'job_position': {
                    'id': job_position.id,
                    'name': job_position.name,
                    'company_name': job_position.company_name,
                    'description': job_position.description
                },
                'resume': {
                    'id': resume.id,
                    'name': resume.name,
                    'expected_position': resume.expected_position
                },
                'questions': questions
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
@login_required
def get_interview_history(request):
    """获取面试问题生成历史"""
    try:
        from .models import InterviewQuestion
        
        # 获取用户的面试问题历史
        history = InterviewQuestion.objects.filter(
            resume__user=request.user
        ).select_related('job_position', 'resume').order_by('-created_at')[:20]
        
        history_data = []
        for record in history:
            history_data.append({
                'id': record.id,
                'job_position': {
                    'name': record.job_position.name,
                    'company_name': record.job_position.company_name
                },
                'resume_name': record.resume.name,
                'questions_count': len(record.questions),
                'created_at': record.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'data': history_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
@login_required
def get_interview_detail(request, interview_id):
    """获取面试问题详情"""
    try:
        from .models import InterviewQuestion
        
        interview = get_object_or_404(InterviewQuestion, id=interview_id)
        
        # 检查权限
        if interview.resume.user != request.user:
            return JsonResponse({
                'success': False,
                'error': '无权访问此记录'
            }, status=403)
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': interview.id,
                'job_position': {
                    'name': interview.job_position.name,
                    'company_name': interview.job_position.company_name,
                    'description': interview.job_position.description
                },
                'resume': {
                    'name': interview.resume.name,
                    'expected_position': interview.resume.expected_position
                },
                'questions': interview.questions,
                'generation_context': interview.generation_context,
                'created_at': interview.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }, status=500)
