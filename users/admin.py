from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Resume, WorkExperience, ProjectExperience, EducationExperience, CustomSection

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering = ('username',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('额外信息', {'fields': ('phone', 'avatar')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('额外信息', {'fields': ('phone', 'avatar')}),
    )

class WorkExperienceInline(admin.TabularInline):
    model = WorkExperience
    extra = 1
    fields = ('start_date', 'end_date', 'company_name', 'department', 'position', 'work_content', 'is_internship')

class ProjectExperienceInline(admin.TabularInline):
    model = ProjectExperience
    extra = 1
    fields = ('start_date', 'end_date', 'project_name', 'project_role', 'project_link', 'project_content')

class EducationExperienceInline(admin.TabularInline):
    model = EducationExperience
    extra = 1
    fields = ('start_date', 'end_date', 'school_name', 'education_level', 'major', 'school_experience')

class CustomSectionInline(admin.TabularInline):
    model = CustomSection
    extra = 1
    fields = ('title', 'content')

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'age', 'education_level', 'expected_position', 'created_at')
    list_filter = ('education_level', 'created_at')
    search_fields = ('user__username', 'name', 'expected_position')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [WorkExperienceInline, ProjectExperienceInline, EducationExperienceInline, CustomSectionInline]

@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display = ('resume', 'company_name', 'position', 'start_date', 'end_date', 'is_internship')
    list_filter = ('is_internship', 'start_date', 'end_date')
    search_fields = ('company_name', 'position', 'department')
    readonly_fields = ('created_at',)

@admin.register(ProjectExperience)
class ProjectExperienceAdmin(admin.ModelAdmin):
    list_display = ('resume', 'project_name', 'project_role', 'start_date', 'end_date')
    list_filter = ('start_date', 'end_date')
    search_fields = ('project_name', 'project_role')
    readonly_fields = ('created_at',)

@admin.register(EducationExperience)
class EducationExperienceAdmin(admin.ModelAdmin):
    list_display = ('resume', 'school_name', 'education_level', 'major', 'start_date', 'end_date')
    list_filter = ('education_level', 'start_date', 'end_date')
    search_fields = ('school_name', 'major')
    readonly_fields = ('created_at',)

@admin.register(CustomSection)
class CustomSectionAdmin(admin.ModelAdmin):
    list_display = ('resume', 'title', 'content_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'content')
    readonly_fields = ('created_at',)
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '内容预览'
