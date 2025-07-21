import jwt
from django.conf import settings
from asgiref.sync import sync_to_async

class JwtHeaderOrUrlAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        headers = dict((k.decode(), v.decode()) for k, v in scope.get('headers', []))
        auth_header = headers.get('authorization')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            from urllib.parse import parse_qs
            query_string = scope.get('query_string', b'').decode()
            token = parse_qs(query_string).get('token', [None])[0]
        print("[中间件] 解析到token:", token)
        user = None
        if token:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                # 使用simplejwt库验证token - 将导入移到这里避免启动问题
                try:
                    from rest_framework_simplejwt.tokens import UntypedToken
                    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
                    
                    # 验证token是否有效
                    UntypedToken(token)
                    # 解码token获取payload
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                    print("[中间件] jwt payload:", payload)
                    user_id = payload.get('user_id')
                    if user_id:
                        user = await sync_to_async(User.objects.get)(id=user_id)
                        print("[中间件] user查找成功:", user)
                    else:
                        print("[中间件] token中没有user_id字段")
                        user = None
                except (InvalidToken, TokenError) as e:
                    print("[中间件] simplejwt token验证失败:", e)
                    user = None
                    
            except Exception as e:
                print("[中间件] jwt解析或user查找失败:", e)
                user = None
        if not user:
            from django.contrib.auth.models import AnonymousUser
            user = AnonymousUser()
            print("[中间件] user为AnonymousUser")
        scope['user'] = user
        return await self.app(scope, receive, send) 