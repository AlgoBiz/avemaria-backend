from django.contrib import admin
from .models import Enquiry

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('candidate_name', 'email', 'topic', 'enquiry_type', 'routed_to_email', 'status', 'is_active', 'is_deleted', 'created_at')
    list_filter = ('status', 'enquiry_type', 'is_active', 'is_deleted', 'created_at')
    search_fields = ('candidate_name', 'email', 'topic', 'enquiry_type', 'faculty_name', 'custom_requirement', 'routed_to_email', 'message')
