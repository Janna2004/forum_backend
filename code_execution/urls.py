from django.urls import path
from .views import RunCodeView

urlpatterns = [
    path('run-code/', RunCodeView.as_view()),
]
