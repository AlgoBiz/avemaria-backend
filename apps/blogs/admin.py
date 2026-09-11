from django.contrib import admin
from .models import Blog

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author_name', 'publish_date', 'is_published')
    list_filter = ('category', 'is_published', 'publish_date')
    search_fields = ('title', 'sub_heading', 'author_name')
    prepopulated_fields = {'slug': ('title',)}
