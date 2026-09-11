from django.contrib import admin
from .models import Enquiry

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('candidate_name', 'email', 'topic', 'status', 'is_active', 'is_deleted', 'created_at')
    list_filter = ('status', 'is_active', 'is_deleted', 'created_at')
    search_fields = ('candidate_name', 'email', 'topic', 'message')
