from django.contrib import admin
from .models import PaidResource, ResourcePDF, ResourcePurchase

class ResourcePDFInline(admin.TabularInline):
    model = ResourcePDF
    extra = 1

@admin.register(PaidResource)
class PaidResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'currency', 'pdf_count', 'is_active', 'is_deleted', 'created_at')
    list_filter = ('category', 'is_active', 'is_deleted')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ResourcePDFInline]

@admin.register(ResourcePurchase)
class ResourcePurchaseAdmin(admin.ModelAdmin):
    list_display = ('student', 'resource', 'payment_status', 'status', 'amount_paid', 'currency', 'purchased_at', 'download_count')
    list_filter = ('payment_status', 'status', 'purchased_at')
    search_fields = ('student__name', 'student__email', 'resource__title', 'order_id')


