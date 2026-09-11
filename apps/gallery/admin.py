from django.contrib import admin
from .models import GalleryItem

@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ('caption', 'category', 'is_active', 'is_deleted', 'order', 'created_at')
    list_filter = ('category', 'is_active', 'is_deleted')
    search_fields = ('caption', 'alt_text')
