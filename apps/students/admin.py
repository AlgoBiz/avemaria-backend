from django.contrib import admin
from .models import Student, StudentDocument

class StudentDocumentInline(admin.TabularInline):
    model = StudentDocument
    extra = 1
    readonly_fields = ('file_size', 'uploaded_at')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'user', 'qualification', 'location', 'status', 'is_active', 'is_deleted', 'registered_date')
    list_filter = ('status', 'qualification', 'is_active', 'is_deleted', 'registered_date')
    search_fields = ('name', 'email', 'qualification', 'institution', 'location')
    inlines = [StudentDocumentInline]

@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'document_type', 'file_name', 'file_size', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('title', 'student__name', 'student__email', 'file_name')
