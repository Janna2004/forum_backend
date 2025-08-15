from django.urls import path
from .views import (
    RunCodeView,
    ProblemBankListView,
    ProblemListView,
    get_problem_detail,
    get_categories,
    search_problems,
    submit_answers,
    get_submission_history,
    get_submission_detail
)

urlpatterns = [
    # 代码执行接口
    path('run-code/', RunCodeView.as_view(), name='run_code'),

    # 题库相关接口
    path('problem-banks/', ProblemBankListView.as_view(), name='problem_banks'),
    path('problem-banks/<str:problem_set_id>/problems/', ProblemListView.as_view(), name='problem_list'),
    path('problems/<str:problem_id>/', get_problem_detail, name='problem_detail'),
    path('categories/', get_categories, name='categories'),
    path('search/', search_problems, name='search_problems'),

    # 答题评析相关接口
    path('problem-banks/<str:problem_set_id>/submit/', submit_answers, name='submit_answers'),
    path('submissions/', get_submission_history, name='submission_history'),
    path('submissions/<int:submission_id>/', get_submission_detail, name='submission_detail'),
]
