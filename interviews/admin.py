from django.contrib import admin
from .models import Interview, InterviewAnswer, CodingProblem, CodingExample, InterviewCodingAnswer

# Register your models here.

@admin.register(CodingProblem)
class CodingProblemAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'difficulty', 'created_at']
    list_filter = ['difficulty', 'created_at']
    search_fields = ['number', 'title', 'description']
    readonly_fields = ['created_at', 'updated_at']

class CodingExampleInline(admin.TabularInline):
    model = CodingExample
    extra = 1

@admin.register(CodingExample)
class CodingExampleAdmin(admin.ModelAdmin):
    list_display = ['problem', 'order', 'input_data', 'output_data']
    list_filter = ['problem']

@admin.register(InterviewCodingAnswer)
class InterviewCodingAnswerAdmin(admin.ModelAdmin):
    list_display = ['user', 'problem', 'language', 'created_at']
    list_filter = ['language', 'created_at']
    search_fields = ['user__username', 'problem__title']
    readonly_fields = ['created_at']
