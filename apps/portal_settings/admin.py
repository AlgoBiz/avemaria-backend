from django.contrib import admin
from .models import PortalSetting

@admin.register(PortalSetting)
class PortalSettingAdmin(admin.ModelAdmin):
    list_display = ('institution_legal_name', 'admissions_email', 'direct_telephone', 'updated_at')
