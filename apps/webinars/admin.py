from django.contrib import admin
from .models import Webinar


@admin.register(Webinar)
class WebinarAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'type',
        'scheduled_date',
        'timing',
        'platform',
        'speaker',
        'status',
        'created_at'
    )
    list_filter = ('type', 'status', 'platform', 'scheduled_date', 'is_deleted')
    search_fields = ('title', 'summary_description', 'outline_agenda', 'speaker__name', 'platform')
    ordering = ('-scheduled_date', '-created_at')
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['speaker']
