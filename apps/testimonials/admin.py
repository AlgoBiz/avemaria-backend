from django.contrib import admin
from .models import Testimonial

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('candidate_name', 'result_placement', 'country', 'rating', 'is_featured', 'is_active', 'is_deleted', 'created_at')
    list_filter = ('rating', 'is_featured', 'is_active', 'is_deleted', 'country')
    search_fields = ('candidate_name', 'quote', 'result_placement')
