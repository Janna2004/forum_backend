"""
自定义中间件
"""
import re
from django.http import HttpResponsePermanentRedirect
from django.conf import settings


class URLStandardizationMiddleware:
    """
    URL标准化中间件
    自动为API请求添加斜杠，但避免POST请求的重定向问题
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # 定义需要标准化的URL模式（API接口）
        self.api_patterns = [
            r'^/users/register$',
            r'^/users/login$',
            r'^/posts/create$',
            r'^/posts/list$',
            r'^/posts/chat$',
            r'^/users/profile$',
            r'^/users/resume$',
            r'^/users/resume/create$',
            r'^/users/resume/work$',
            r'^/users/resume/project$',
            r'^/users/resume/education$',
            r'^/users/resume/custom$',
            r'^/users/resume/work/delete$',
            r'^/users/resume/project/delete$',
            r'^/users/resume/education/delete$',
            r'^/users/resume/custom/delete$',
        ]
        self.api_patterns = [re.compile(pattern) for pattern in self.api_patterns]
    
    def __call__(self, request):
        # 检查是否是API请求且需要添加斜杠
        if self._should_add_slash(request):
            # 对于GET请求，进行重定向
            if request.method == 'GET':
                return HttpResponsePermanentRedirect(request.path + '/')
            # 对于POST/PUT/DELETE等请求，直接修改request.path
            else:
                # 修改request对象的路径
                original_path = request.path
                original_path_info = request.path_info
                
                request.path = request.path + '/'
                request.path_info = request.path_info + '/'
                # 同时修改META中的PATH_INFO
                request.META['PATH_INFO'] = request.path_info
                
                # 调试信息
                if settings.DEBUG:
                    print(f"URL标准化: {original_path} -> {request.path}")
        
        response = self.get_response(request)
        return response
    
    def _should_add_slash(self, request):
        """判断是否需要添加斜杠"""
        # 如果URL已经以斜杠结尾，不需要处理
        if request.path.endswith('/'):
            return False
        
        # 检查是否匹配API模式
        for pattern in self.api_patterns:
            if pattern.match(request.path):
                return True
        
        return False


class CORSFixMiddleware:
    """
    CORS修复中间件
    确保CORS头部正确设置
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # 确保CORS头部设置正确
        if hasattr(settings, 'CORS_ALLOW_ALL_ORIGINS') and settings.CORS_ALLOW_ALL_ORIGINS:
            response['Access-Control-Allow-Origin'] = '*'
        
        if hasattr(settings, 'CORS_ALLOW_CREDENTIALS') and settings.CORS_ALLOW_CREDENTIALS:
            response['Access-Control-Allow-Credentials'] = 'true'
        
        return response 