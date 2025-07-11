# type: ignore[attr-defined]
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from users.views import jwt_required
from .models import Post
import json
from django.core.paginator import Paginator
import websocket
import json
import time
import hashlib
import base64
import hmac
from urllib.parse import urlencode
from datetime import datetime
from django.http import StreamingHttpResponse
from django.conf import settings

# Create your views here.

@csrf_exempt
@jwt_required
def create_post(request):
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        data = json.loads(request.body.decode())
        title = data.get('title')
        content = data.get('content')
        if not title or not content:
            return JsonResponse({'error': '标题和内容不能为空'}, status=400)
        post = Post.objects.create(title=title, content=content, author=request.user)
        return JsonResponse({'msg': '发帖成功', 'post_id': post.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@jwt_required
def delete_post(request, post_id):
    if request.method not in ['POST', 'DELETE']:
        return JsonResponse({'error': '仅支持POST或DELETE请求'}, status=405)
    try:
        post = Post.objects.get(id=post_id)
        if post.author != request.user:
            return JsonResponse({'error': '无权限删除他人帖子'}, status=403)
        post.delete()
        return JsonResponse({'msg': '删除成功'})
    except Post.DoesNotExist:
        return JsonResponse({'error': '帖子不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@jwt_required
def update_post(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        post = Post.objects.get(id=post_id)
        if post.author != request.user:
            return JsonResponse({'error': '无权限修改他人帖子'}, status=403)
        data = json.loads(request.body.decode())
        title = data.get('title')
        content = data.get('content')
        if title:
            post.title = title
        if content:
            post.content = content
        post.save()
        return JsonResponse({'msg': '修改成功'})
    except Post.DoesNotExist:
        return JsonResponse({'error': '帖子不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def list_posts(request):
    if request.method != 'GET':
        return JsonResponse({'error': '仅支持GET请求'}, status=405)
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        posts = Post.objects.all().order_by('-created_at')
        paginator = Paginator(posts, page_size)
        page_obj = paginator.get_page(page)
        data = [
            {
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'author': post.author.username,
                'created_at': post.created_at,
                'updated_at': post.updated_at
            }
            for post in page_obj
        ]
        return JsonResponse({
            'results': data,
            'total': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def create_url():
    """生成讯飞API请求URL"""
    url = 'wss://spark-api.xf-yun.com/v3.1/chat'
    # 生成RFC1123格式的时间戳
    now = datetime.now()
    date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    # 拼接字符串
    signature_origin = "host: " + "spark-api.xf-yun.com" + "\n"
    signature_origin += "date: " + date + "\n"
    signature_origin += "GET " + "/v3.1/chat" + " HTTP/1.1"
    
    # 进行hmac-sha256进行加密
    signature_sha = hmac.new(
        settings.XUNFEI_API_SECRET.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    
    signature_sha_base64 = base64.b64encode(signature_sha).decode()
    authorization_origin = f'api_key="{settings.XUNFEI_API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode()
    
    # 将请求的鉴权参数组合为字典
    v = {
        "authorization": authorization,
        "date": date,
        "host": "spark-api.xf-yun.com"
    }
    # 拼接鉴权参数，生成url
    url = url + '?' + urlencode(v)
    return url

@csrf_exempt
def chat_with_ai(request):
    """讯飞大模型对话接口"""
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    
    try:
        data = json.loads(request.body.decode())
        message = data.get('message', '')
        if not message:
            return JsonResponse({'error': '消息不能为空'}, status=400)
        
        def generate_response():
            """生成流式响应"""
            url = create_url()
            ws = websocket.create_connection(url)
            
            # 构建请求数据
            data = {
                "header": {
                    "app_id": settings.XUNFEI_APP_ID,
                    "uid": "12345"
                },
                "parameter": {
                    "chat": {
                        "domain": "general",
                        "temperature": 0.5,
                        "max_tokens": 2048
                    }
                },
                "payload": {
                    "message": {
                        "text": [
                            {"role": "user", "content": message}
                        ]
                    }
                }
            }
            
            ws.send(json.dumps(data))
            
            while True:
                response = ws.recv()
                response_data = json.loads(response)
                
                # 检查是否是最后一条消息
                if response_data['header']['code'] != 0:
                    yield f"data: {json.dumps({'error': '请求失败'})}\n\n"
                    break
                
                # 获取文本内容
                text = response_data['payload']['choices']['text'][0]['content']
                yield f"data: {json.dumps({'content': text})}\n\n"
                
                # 检查是否结束
                if response_data['header']['status'] == 2:
                    break
            
            ws.close()
        
        return StreamingHttpResponse(
            generate_response(),
            content_type='text/plain'
        )
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
