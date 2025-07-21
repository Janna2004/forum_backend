from django.urls import path
from . import views

app_name = 'interviews'

urlpatterns = [
    path('create/', views.InterviewCreateView.as_view(), name='create'),
    path('list/', views.InterviewListView.as_view(), name='list'),
] 