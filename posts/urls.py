from django.urls import path
from .views import create_post, delete_post, update_post, list_posts, chat_with_ai

urlpatterns = [
    path('create/', create_post, name='create_post'),
    path('delete/<int:post_id>/', delete_post, name='delete_post'),
    path('update/<int:post_id>/', update_post, name='update_post'),
    path('list/', list_posts, name='list_posts'),
    path('chat/', chat_with_ai, name='chat_with_ai'),
] 