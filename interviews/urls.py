from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

app_name = 'interviews'

urlpatterns = [
    path('create/', views.InterviewCreateView.as_view(), name='create'),
    path('list/', views.InterviewListView.as_view(), name='list'),
    path('coding-problems/', views.list_coding_problems, name='list_coding_problems'),
    path('coding-problems/<int:problem_id>/', views.get_coding_problem_detail, name='get_coding_problem_detail'),
    path('<int:interview_id>/scores/', views.get_interview_scores, name='get_interview_scores'),
    path('evaluation/', views.get_interview_evaluation, name='interview_evaluation'),
    path('evaluation/overview/', views.get_user_evaluation_overview, name='user_evaluation_overview'),
]

# 添加格式后缀支持
urlpatterns = format_suffix_patterns(urlpatterns)