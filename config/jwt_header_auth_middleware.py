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
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                print("[中间件] jwt payload:", payload)
                user = await sync_to_async(User.objects.get)(id=payload['user_id'])
                print("[中间件] user查找成功:", user)
            except Exception as e:
                print("[中间件] jwt解析或user查找失败:", e)
                user = None
        if not user:
            from django.contrib.auth.models import AnonymousUser
            user = AnonymousUser()
            print("[中间件] user为AnonymousUser")
        scope['user'] = user
        return await self.app(scope, receive, send) 