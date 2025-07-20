from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from .models import Resume, WorkExperience, ProjectExperience, EducationExperience, CustomSection
import json
from django.contrib.auth import authenticate
from django.conf import settings
from datetime import datetime, timedelta
from django.views.decorators.http import require_http_methods
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

# Create your views here.

@csrf_exempt
def register(request):
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        data = json.loads(request.body.decode())
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return JsonResponse({'error': '用户名和密码不能为空'}, status=400)
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': '用户名已存在'}, status=400)
        user = User.objects.create_user(username=username, password=password)
        return JsonResponse({'msg': '注册成功', 'user_id': user.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def login_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        # 添加调试信息
        if settings.DEBUG:
            print(f"登录请求路径: {request.path}")
            print(f"请求内容类型: {request.content_type}")
            print(f"请求体长度: {len(request.body) if request.body else 0}")
        
        # 检查请求体是否为空
        if not request.body:
            return JsonResponse({'error': '请求体不能为空'}, status=400)
        
        data = json.loads(request.body.decode())
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return JsonResponse({'error': '用户名和密码不能为空'}, status=400)
        
        user = authenticate(username=username, password=password)
        if user is None:
            return JsonResponse({'error': '用户名或密码错误'}, status=400)
        
        # 使用 SimpleJWT 生成 token
        refresh = RefreshToken.for_user(user)
        
        return JsonResponse({
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'user_id': user.id,
            'username': user.username,
            'msg': '登录成功'
        })
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'JSON解析错误: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """获取用户个人信息"""
    try:
        user = request.user
        profile_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone,
            'avatar': user.avatar,
            'date_joined': user.date_joined,
            'last_login': user.last_login
        }
        
        # 获取简历信息
        try:
            resume = user.resume
            profile_data['resume'] = {
                'id': resume.id,
                'name': resume.name,
                'age': resume.age,
                'graduation_date': resume.graduation_date.isoformat() if resume.graduation_date else None,
                'education_level': resume.education_level,
                'expected_position': resume.expected_position,
                'created_at': resume.created_at.isoformat(),
                'updated_at': resume.updated_at.isoformat()
            }
        except Resume.DoesNotExist:
            profile_data['resume'] = None
        
        return JsonResponse({
            'success': True,
            'profile': profile_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    """更新用户个人信息"""
    try:
        user = request.user
        data = json.loads(request.body.decode())
        
        # 更新基本信息
        if 'email' in data:
            user.email = data['email']
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'avatar' in data:
            user.avatar = data['avatar']
        
        user.save()
        
        return JsonResponse({
            'success': True,
            'msg': '个人信息更新成功'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_resume(request):
    """获取用户简历详细信息"""
    try:
        user = request.user
        
        try:
            resume = user.resume
        except Resume.DoesNotExist:
            return JsonResponse({
                'success': True,
                'resume': None,
                'msg': '简历不存在'
            })
        
        # 构建简历数据
        resume_data = {
            'id': resume.id,
            'name': resume.name,
            'age': resume.age,
            'graduation_date': resume.graduation_date.isoformat() if resume.graduation_date else None,
            'education_level': resume.education_level,
            'expected_position': resume.expected_position,
            'created_at': resume.created_at.isoformat(),
            'updated_at': resume.updated_at.isoformat(),
            
            # 工作经历
            'work_experiences': [
                {
                    'id': exp.id,
                    'start_date': exp.start_date.isoformat(),
                    'end_date': exp.end_date.isoformat() if exp.end_date else None,
                    'company_name': exp.company_name,
                    'department': exp.department,
                    'position': exp.position,
                    'work_content': exp.work_content,
                    'is_internship': exp.is_internship
                }
                for exp in resume.work_experiences.all()
            ],
            
            # 项目经历
            'project_experiences': [
                {
                    'id': exp.id,
                    'start_date': exp.start_date.isoformat(),
                    'end_date': exp.end_date.isoformat() if exp.end_date else None,
                    'project_name': exp.project_name,
                    'project_role': exp.project_role,
                    'project_link': exp.project_link,
                    'project_content': exp.project_content
                }
                for exp in resume.project_experiences.all()
            ],
            
            # 教育经历
            'education_experiences': [
                {
                    'id': exp.id,
                    'start_date': exp.start_date.isoformat(),
                    'end_date': exp.end_date.isoformat() if exp.end_date else None,
                    'school_name': exp.school_name,
                    'education_level': exp.education_level,
                    'major': exp.major,
                    'school_experience': exp.school_experience
                }
                for exp in resume.education_experiences.all()
            ],
            
            # 自定义部分
            'custom_sections': [
                {
                    'id': section.id,
                    'title': section.title,
                    'content': section.content
                }
                for section in resume.custom_sections.all()
            ]
        }
        
        return JsonResponse({
            'success': True,
            'resume': resume_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@permission_classes([IsAuthenticated])
def create_or_update_resume(request):
    """创建或更新简历"""
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        user = request.user
        data = json.loads(request.body.decode())
        
        # 检查是否已存在简历
        try:
            resume = Resume.objects.get(user=user)
            created = False
        except Resume.DoesNotExist:
            # 创建新简历时，需要提供所有必填字段
            if not all(key in data for key in ['name', 'age', 'graduation_date', 'education_level', 'expected_position']):
                return JsonResponse({
                    'error': '创建简历时需要提供所有必填字段：name, age, graduation_date, education_level, expected_position'
                }, status=400)
            
            resume = Resume.objects.create(
                user=user,
                name=data['name'],
                age=data['age'],
                graduation_date=data['graduation_date'],
                education_level=data['education_level'],
                expected_position=data['expected_position']
            )
            created = True
        else:
            # 更新现有简历
            if 'name' in data:
                resume.name = data['name']
            if 'age' in data:
                resume.age = data['age']
            if 'graduation_date' in data:
                resume.graduation_date = data['graduation_date']
            if 'education_level' in data:
                resume.education_level = data['education_level']
            if 'expected_position' in data:
                resume.expected_position = data['expected_position']
            
            resume.save()
        
        return JsonResponse({
            'success': True,
            'msg': '简历创建成功' if created else '简历更新成功',
            'resume_id': resume.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@permission_classes([IsAuthenticated])
def manage_work_experience(request):
    """管理工作经历：创建（不传id）或更新（传id）"""
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        user = request.user
        data = json.loads(request.body.decode())
        resume = get_object_or_404(Resume, user=user)
        work_id = data.get('work_id')
        
        if work_id is not None:
            # 更新：通过用户ID+工作经历ID验证权限
            work_exp = get_object_or_404(WorkExperience, id=work_id, resume__user=user)
            for field in ['start_date', 'end_date', 'company_name', 'department', 'position', 'work_content', 'is_internship']:
                if field in data:
                    setattr(work_exp, field, data[field])
            work_exp.save()
            return JsonResponse({'success': True, 'msg': '工作经历更新成功', 'work_experience_id': work_exp.id})
        else:
            # 创建：不传ID，后端自动生成
            work_exp = WorkExperience.objects.create(
                resume=resume,
                start_date=data['start_date'],
                end_date=data.get('end_date'),
                company_name=data['company_name'],
                department=data.get('department'),
                position=data.get('position'),
                work_content=data['work_content'],
                is_internship=data.get('is_internship', False)
            )
            return JsonResponse({'success': True, 'msg': '工作经历创建成功', 'work_experience_id': work_exp.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@permission_classes([IsAuthenticated])
def manage_project_experience(request):
    """管理项目经历：创建（不传id）或更新（传id）"""
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        user = request.user
        data = json.loads(request.body.decode())
        resume = get_object_or_404(Resume, user=user)
        project_id = data.get('project_id')
        
        if project_id is not None:
            # 更新：通过用户ID+项目经历ID验证权限
            project_exp = get_object_or_404(ProjectExperience, id=project_id, resume__user=user)
            for field in ['start_date', 'end_date', 'project_name', 'project_role', 'project_link', 'project_content']:
                if field in data:
                    setattr(project_exp, field, data[field])
            project_exp.save()
            return JsonResponse({'success': True, 'msg': '项目经历更新成功', 'project_experience_id': project_exp.id})
        else:
            # 创建：不传ID，后端自动生成
            project_exp = ProjectExperience.objects.create(
                resume=resume,
                start_date=data['start_date'],
                end_date=data.get('end_date'),
                project_name=data['project_name'],
                project_role=data['project_role'],
                project_link=data.get('project_link'),
                project_content=data['project_content']
            )
            return JsonResponse({'success': True, 'msg': '项目经历创建成功', 'project_experience_id': project_exp.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@permission_classes([IsAuthenticated])
def manage_education_experience(request):
    """管理教育经历：创建（不传id）或更新（传id）"""
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        user = request.user
        data = json.loads(request.body.decode())
        resume = get_object_or_404(Resume, user=user)
        education_id = data.get('education_id')
        
        if education_id is not None:
            # 更新：通过用户ID+教育经历ID验证权限
            education_exp = get_object_or_404(EducationExperience, id=education_id, resume__user=user)
            for field in ['start_date', 'end_date', 'school_name', 'education_level', 'major', 'school_experience']:
                if field in data:
                    setattr(education_exp, field, data[field])
            education_exp.save()
            return JsonResponse({'success': True, 'msg': '教育经历更新成功', 'education_experience_id': education_exp.id})
        else:
            # 创建：不传ID，后端自动生成
            education_exp = EducationExperience.objects.create(
                resume=resume,
                start_date=data['start_date'],
                end_date=data.get('end_date'),
                school_name=data['school_name'],
                education_level=data['education_level'],
                major=data.get('major'),
                school_experience=data.get('school_experience')
            )
            return JsonResponse({'success': True, 'msg': '教育经历创建成功', 'education_experience_id': education_exp.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@permission_classes([IsAuthenticated])
def manage_custom_section(request):
    """管理自定义部分：创建（不传id）或更新（传id）"""
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        user = request.user
        data = json.loads(request.body.decode())
        resume = get_object_or_404(Resume, user=user)
        custom_id = data.get('custom_id')
        
        if custom_id is not None:
            # 更新：通过用户ID+自定义部分ID验证权限
            custom_section = get_object_or_404(CustomSection, id=custom_id, resume__user=user)
            for field in ['title', 'content']:
                if field in data:
                    setattr(custom_section, field, data[field])
            custom_section.save()
            return JsonResponse({'success': True, 'msg': '自定义部分更新成功', 'custom_section_id': custom_section.id})
        else:
            # 创建：不传ID，后端自动生成
            custom_section = CustomSection.objects.create(
                resume=resume,
                title=data['title'],
                content=data['content']
            )
            return JsonResponse({'success': True, 'msg': '自定义部分创建成功', 'custom_section_id': custom_section.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@permission_classes([IsAuthenticated])
def delete_work_experience(request):
    """删除工作经历"""
    if request.method != 'DELETE':
        return JsonResponse({'error': '仅支持DELETE请求'}, status=405)
    try:
        user = request.user
        data = json.loads(request.body.decode())
        work_id = data.get('work_id')
        
        if not work_id:
            return JsonResponse({'error': '缺少work_id参数'}, status=400)
        
        # 通过用户ID+工作经历ID验证权限
        work_exp = get_object_or_404(WorkExperience, id=work_id, resume__user=user)
        work_exp.delete()
        
        return JsonResponse({
            'success': True,
            'msg': '工作经历删除成功'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@permission_classes([IsAuthenticated])
def delete_project_experience(request):
    """删除项目经历"""
    if request.method != 'DELETE':
        return JsonResponse({'error': '仅支持DELETE请求'}, status=405)
    try:
        user = request.user
        data = json.loads(request.body.decode())
        project_id = data.get('project_id')
        
        if not project_id:
            return JsonResponse({'error': '缺少project_id参数'}, status=400)
        
        # 通过用户ID+项目经历ID验证权限
        project_exp = get_object_or_404(ProjectExperience, id=project_id, resume__user=user)
        project_exp.delete()
        
        return JsonResponse({
            'success': True,
            'msg': '项目经历删除成功'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@permission_classes([IsAuthenticated])
def delete_education_experience(request):
    """删除教育经历"""
    if request.method != 'DELETE':
        return JsonResponse({'error': '仅支持DELETE请求'}, status=405)
    try:
        user = request.user
        data = json.loads(request.body.decode())
        education_id = data.get('education_id')
        
        if not education_id:
            return JsonResponse({'error': '缺少education_id参数'}, status=400)
        
        # 通过用户ID+教育经历ID验证权限
        education_exp = get_object_or_404(EducationExperience, id=education_id, resume__user=user)
        education_exp.delete()
        
        return JsonResponse({
            'success': True,
            'msg': '教育经历删除成功'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@permission_classes([IsAuthenticated])
def delete_custom_section(request):
    """删除自定义部分"""
    if request.method != 'DELETE':
        return JsonResponse({'error': '仅支持DELETE请求'}, status=405)
    try:
        user = request.user
        data = json.loads(request.body.decode())
        custom_id = data.get('custom_id')
        
        if not custom_id:
            return JsonResponse({'error': '缺少custom_id参数'}, status=400)
        
        # 通过用户ID+自定义部分ID验证权限
        custom_section = get_object_or_404(CustomSection, id=custom_id, resume__user=user)
        custom_section.delete()
        
        return JsonResponse({
            'success': True,
            'msg': '自定义部分删除成功'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
