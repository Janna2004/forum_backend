from django.contrib import admin
from .models import JobPosition, KnowledgeBaseEntry, InterviewQuestion

@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ['name', 'company_name', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'company_name', 'description']
    ordering = ['-created_at']

@admin.register(KnowledgeBaseEntry)
class KnowledgeBaseEntryAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'difficulty_level', 'created_at']
    list_filter = ['category', 'difficulty_level', 'created_at']
    search_fields = ['question', 'answer', 'tags']
    filter_horizontal = ['related_positions']
    ordering = ['-created_at']

@admin.register(InterviewQuestion)
class InterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ['job_position', 'resume', 'created_at']
    list_filter = ['created_at']
    search_fields = ['job_position__name', 'resume__name']
    readonly_fields = ['questions', 'generation_context']
    ordering = ['-created_at']
