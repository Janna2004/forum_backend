from django.urls import path
from .views import (
    create_post, delete_post, update_post, list_posts, chat_with_ai,
    get_post_detail, create_reply, update_reply, delete_reply
)

urlpatterns = [
    path('create/', create_post, name='create_post'),
    path('delete/<int:post_id>/', delete_post, name='delete_post'),
    path('update/<int:post_id>/', update_post, name='update_post'),
    path('list/', list_posts, name='list_posts'),
    path('detail/<int:post_id>/', get_post_detail, name='get_post_detail'),
    path('chat/', chat_with_ai, name='chat_with_ai'),
    
    # 回复相关接口
    path('reply/create/<int:post_id>/', create_reply, name='create_reply'),
    path('reply/update/<int:reply_id>/', update_reply, name='update_reply'),
    path('reply/delete/<int:reply_id>/', delete_reply, name='delete_reply'),
] 