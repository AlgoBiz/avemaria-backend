from django.db import models
from core.models import BaseModel

class Testimonial(BaseModel):
    candidate_name = models.CharField(max_length=150)
    initials = models.CharField(max_length=10, blank=True)
    programme_name = models.CharField(max_length=255, blank=True, default='', help_text="Enrolled programme / course name")
    result_placement = models.CharField(max_length=200, blank=True, default='', help_text="e.g. DHA Licence cleared — first attempt")
    country = models.CharField(max_length=100, blank=True, default='', help_text="e.g. United Arab Emirates")
    quote = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    photo = models.ImageField(upload_to='testimonials/', null=True, blank=True)
    is_published = models.BooleanField(default=True, help_text="True for Published, False for Unpublished / Draft")
    is_student_submission = models.BooleanField(default=False, help_text="Direct student feedback submission")
    is_featured = models.BooleanField(default=True)
    slug = models.SlugField(max_length=180, blank=True, default='', db_index=True)

    class Meta:
        verbose_name = 'Student Testimonial'
        verbose_name_plural = 'Student Testimonials'
        ordering = ['-created_at', '-id']

    def save(self, *args, **kwargs):
        if not self.initials and self.candidate_name:
            parts = self.candidate_name.strip().split()
            if len(parts) >= 2:
                self.initials = f"{parts[0][0]}{parts[-1][0]}".upper()
            elif len(parts) == 1:
                self.initials = parts[0][:2].upper()
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.candidate_name) or 'testimonial'
            unique_slug = base_slug
            counter = 1
            while Testimonial.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.candidate_name} ({self.country}) - {self.rating}★"
