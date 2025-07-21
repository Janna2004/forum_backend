from django.urls import path
from . import views

app_name = 'interviews'

urlpatterns = [
    path('create/', views.InterviewCreateView.as_view(), name='create'),
    path('list/', views.InterviewListView.as_view(), name='list'),
    path('coding-problems/', views.list_coding_problems, name='list_coding_problems'),
    path('coding-problems/<int:problem_id>/', views.get_coding_problem_detail, name='get_coding_problem_detail'),
] 