from django.contrib import admin
from .models import Faculty


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'qualification', 'department', 'is_published', 'is_featured', 'display_order', 'created_at')
    list_filter = ('is_published', 'is_featured', 'department', 'is_deleted')
    search_fields = ('name', 'title', 'qualification', 'department', 'bio')
    ordering = ('display_order', '-created_at')
