# type: ignore[attr-defined]
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from users.views import jwt_required
from .models import Post, Reply
import json
from django.core.paginator import Paginator
import websocket
from websocket import WebSocketBadStatusException
import json
import time
import hashlib
import base64
import hmac
from urllib.parse import urlencode
from datetime import datetime, timezone
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
                'updated_at': post.updated_at,
                'reply_count': post.replies.count()
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

@csrf_exempt
def get_post_detail(request, post_id):
    """获取帖子详细信息，包含所有回复"""
    if request.method != 'GET':
        return JsonResponse({'error': '仅支持GET请求'}, status=405)
    try:
        post = get_object_or_404(Post, id=post_id)
        
        # 获取所有回复（包括嵌套回复）
        def get_replies_with_children(parent_reply=None):
            """递归获取回复及其子回复"""
            replies = Reply.objects.filter(post=post, parent_reply=parent_reply).order_by('created_at')
            result = []
            for reply in replies:
                reply_data = {
                    'id': reply.id,
                    'content': reply.content,
                    'author': reply.author.username,
                    'created_at': reply.created_at,
                    'updated_at': reply.updated_at,
                    'parent_reply_id': reply.parent_reply.id if reply.parent_reply else None,
                    'child_replies': get_replies_with_children(reply)
                }
                result.append(reply_data)
            return result
        
        # 构建帖子详细信息
        post_data = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'author': post.author.username,
            'created_at': post.created_at,
            'updated_at': post.updated_at,
            'reply_count': post.replies.count(),
            'replies': get_replies_with_children()
        }
        
        return JsonResponse({
            'success': True,
            'post': post_data
        })
        
    except Post.DoesNotExist:
        return JsonResponse({'error': '帖子不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@jwt_required
def create_reply(request, post_id):
    """创建回复"""
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        post = get_object_or_404(Post, id=post_id)
        data = json.loads(request.body.decode())
        content = data.get('content')
        parent_reply_id = data.get('parent_reply_id')  # 可选，用于嵌套回复
        
        if not content:
            return JsonResponse({'error': '回复内容不能为空'}, status=400)
        
        # 创建回复
        reply_data = {
            'post': post,
            'content': content,
            'author': request.user
        }
        
        # 如果有父回复ID，添加父回复关系
        if parent_reply_id:
            try:
                parent_reply = Reply.objects.get(id=parent_reply_id, post=post)
                reply_data['parent_reply'] = parent_reply
            except Reply.DoesNotExist:
                return JsonResponse({'error': '父回复不存在'}, status=404)
        
        reply = Reply.objects.create(**reply_data)
        
        return JsonResponse({
            'success': True,
            'msg': '回复成功',
            'reply': {
                'id': reply.id,
                'content': reply.content,
                'author': reply.author.username,
                'created_at': reply.created_at,
                'parent_reply_id': reply.parent_reply.id if reply.parent_reply else None
            }
        })
        
    except Post.DoesNotExist:
        return JsonResponse({'error': '帖子不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@jwt_required
def update_reply(request, reply_id):
    """更新回复"""
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        reply = get_object_or_404(Reply, id=reply_id)
        
        # 检查权限
        if reply.author != request.user:
            return JsonResponse({'error': '无权限修改他人回复'}, status=403)
        
        data = json.loads(request.body.decode())
        content = data.get('content')
        
        if not content:
            return JsonResponse({'error': '回复内容不能为空'}, status=400)
        
        reply.content = content
        reply.save()
        
        return JsonResponse({
            'success': True,
            'msg': '回复修改成功',
            'reply': {
                'id': reply.id,
                'content': reply.content,
                'author': reply.author.username,
                'updated_at': reply.updated_at
            }
        })
        
    except Reply.DoesNotExist:
        return JsonResponse({'error': '回复不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@jwt_required
def delete_reply(request, reply_id):
    """删除回复"""
    if request.method not in ['POST', 'DELETE']:
        return JsonResponse({'error': '仅支持POST或DELETE请求'}, status=405)
    try:
        reply = get_object_or_404(Reply, id=reply_id)
        
        # 检查权限
        if reply.author != request.user:
            return JsonResponse({'error': '无权限删除他人回复'}, status=403)
        
        reply.delete()
        return JsonResponse({'success': True, 'msg': '回复删除成功'})
        
    except Reply.DoesNotExist:
        return JsonResponse({'error': '回复不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def create_url():
    """生成讯飞API请求URL"""
    url = 'wss://spark-api.xf-yun.com/v3.1/chat'
    
    # 生成RFC1123格式的时间戳
    now = datetime.now(timezone.utc)  # 使用UTC时间
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
    
    # 打印调试信息（生产环境应移除）
    print(f"Debug - Date: {date}")
    print(f"Debug - Signature Origin: {signature_origin}")
    print(f"Debug - API Key: {settings.XUNFEI_API_KEY}")
    print(f"Debug - API Secret: {settings.XUNFEI_API_SECRET}")
    
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
            try:
                url = create_url()
                print(f"正在连接讯飞API: {url}")
                ws = websocket.create_connection(url, timeout=10)
                print("WebSocket连接成功")
                
                # 构建请求数据
                data = {
                    "header": {
                        "app_id": settings.XUNFEI_APP_ID,
                        "uid": "12345"
                    },
                    "parameter": {
                        "chat": {
                            "domain": "generalv3",  # 星火X1模型使用generalv3
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
                
                print(f"发送请求数据: {json.dumps(data, ensure_ascii=False)}")
                ws.send(json.dumps(data))
                
                while True:
                    response = ws.recv()
                    print(f"收到响应: {response}")
                    response_data = json.loads(response)
                    
                    # 检查响应状态
                    if response_data['header']['code'] != 0:
                        error_msg = response_data.get('payload', {}).get('text', '请求失败')
                        print(f"API错误: {error_msg}")
                        yield f"data: {json.dumps({'error': error_msg})}\n\n"
                        break
                    
                    # 检查是否有文本内容
                    if 'payload' in response_data and 'choices' in response_data['payload']:
                        text = response_data['payload']['choices']['text'][0]['content']
                        print(f"AI回复: {text}")
                        yield f"data: {json.dumps({'content': text})}\n\n"
                    else:
                        print(f"响应格式异常: {response_data}")
                        yield f"data: {json.dumps({'error': '响应格式异常'})}\n\n"
                        break
                    
                    # 检查是否结束
                    if response_data['header']['status'] == 2:
                        print("对话结束")
                        break
                
                ws.close()
                
            except WebSocketBadStatusException as e:
                error_msg = f'WebSocket连接失败: {str(e)}'
                print(error_msg)
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
            except Exception as e:
                error_msg = f'请求失败: {str(e)}'
                print(error_msg)
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
        
        return StreamingHttpResponse(
            generate_response(),
            content_type='text/plain'
        )
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
