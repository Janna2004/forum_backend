from django.urls import path
from . import views

app_name = 'knowledge_base'
 
urlpatterns = [
    path('generate-questions/', views.generate_interview_questions, name='generate_questions'),
    path('interview-history/', views.get_interview_history, name='interview_history'),
    path('interview-detail/<int:interview_id>/', views.get_interview_detail, name='interview_detail'),
] 