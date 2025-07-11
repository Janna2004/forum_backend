from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
import json
from django.contrib.auth import authenticate
import jwt
from django.conf import settings
from datetime import datetime, timedelta

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
        data = json.loads(request.body.decode())
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return JsonResponse({'error': '用户名和密码不能为空'}, status=400)
        user = authenticate(username=username, password=password)
        if user is None:
            return JsonResponse({'error': '用户名或密码错误'}, status=400)
        payload = {
            'user_id': user.id,
            'username': user.username,
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return JsonResponse({'token': token, 'msg': '登录成功'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def jwt_required(view_func):
    def wrapper(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': '未提供有效的JWT令牌'}, status=401)
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=payload['user_id'])
            request.user = user
        except Exception as e:
            return JsonResponse({'error': 'JWT无效或已过期'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper
