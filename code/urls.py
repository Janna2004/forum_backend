from django.urls import path
from .views import RunCodeView

urlpatterns = [
    path('run-code/', RunCodeView.as_view()),
    # TODO:url: '/code/languages/', 获取支持的编程语言
    # path('languages/', get_supported_languages, name='get_supported_languages'),
]
