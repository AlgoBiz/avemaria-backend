from django.contrib import admin
from .models import Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'programmes_count', 'is_active', 'is_deleted', 'order', 'created_at')
    list_filter = ('is_active', 'is_deleted')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'description')
