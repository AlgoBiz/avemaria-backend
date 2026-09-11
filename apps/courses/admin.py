from django.contrib import admin
from .models import Course, CourseEnrollment

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'fee', 'currency', 'duration', 'level', 'is_published', 'is_active', 'is_deleted', 'rating')
    list_filter = ('category', 'level', 'is_published', 'is_active', 'is_deleted')
    search_fields = ('title', 'summary', 'faculty_name')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'status', 'progress_percentage', 'enrolled_at')
    list_filter = ('status', 'enrolled_at')
    search_fields = ('student__name', 'student__email', 'course__title')
