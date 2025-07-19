import jwt
from django.conf import settings

class JwtHeaderOrUrlAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # 解析header
        headers = dict((k.decode(), v.decode()) for k, v in scope.get('headers', []))
        auth_header = headers.get('authorization')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        # 解析URL参数
        if not token:
            from urllib.parse import parse_qs
            query_string = scope.get('query_string', b'').decode()
            token = parse_qs(query_string).get('token', [None])[0]
        user = None
        if token:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                user = User.objects.get(id=payload['user_id'])
            except Exception:
                user = None
        if not user:
            from django.contrib.auth.models import AnonymousUser
            user = AnonymousUser()
        scope['user'] = user
        return await self.app(scope, receive, send) 