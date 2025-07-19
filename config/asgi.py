"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from .jwt_header_auth_middleware import JwtHeaderOrUrlAuthMiddleware

def get_websocket_urlpatterns():
    from webrtc.routing import websocket_urlpatterns
    return websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JwtHeaderOrUrlAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                get_websocket_urlpatterns()
            )
        )
    ),
})