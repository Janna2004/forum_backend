from django.urls import path
from .views import (
    register, login_view, get_user_profile, update_user_profile,
    get_resume, create_or_update_resume, manage_work_experience,
    manage_project_experience, manage_education_experience, manage_custom_section,
    delete_work_experience, delete_project_experience, delete_education_experience, delete_custom_section,
    get_user_resumes
)

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    
    # 个人信息管理
    path('profile/', get_user_profile, name='get_user_profile'),
    path('profile/update/', update_user_profile, name='update_user_profile'),
    
    # 简历管理
    path('resume/', get_resume, name='get_resume'),
    path('resume/list/', get_user_resumes, name='get_user_resumes'),  # 获取用户所有简历
    path('resume/create/', create_or_update_resume, name='create_or_update_resume'),
    
    # 工作经历管理
    path('resume/work/', manage_work_experience, name='manage_work_experience'),
    
    # 项目经历管理
    path('resume/project/', manage_project_experience, name='manage_project_experience'),
    
    # 教育经历管理
    path('resume/education/', manage_education_experience, name='manage_education_experience'),
    
    # 自定义部分管理
    path('resume/custom/', manage_custom_section, name='manage_custom_section'),
    
    # 删除接口
    path('resume/work/delete/', delete_work_experience, name='delete_work_experience'),
    path('resume/project/delete/', delete_project_experience, name='delete_project_experience'),
    path('resume/education/delete/', delete_education_experience, name='delete_education_experience'),
    path('resume/custom/delete/', delete_custom_section, name='delete_custom_section'),
] 