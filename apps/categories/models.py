from django.db import models
from django.utils.text import slugify
from core.models import BaseModel

class Category(BaseModel):
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    cover_image = models.ImageField(upload_to='categories/', null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False, help_text="Feature this category on homepage (max 4 allowed)")

    class Meta:
        verbose_name = 'Course Category'
        verbose_name_plural = 'Course Categories'
        ordering = ['-created_at', '-id']

    def save(self, *args, **kwargs):
        if self.is_featured:
            featured_qs = Category.objects.filter(is_featured=True, is_deleted=False)
            if self.pk:
                featured_qs = featured_qs.exclude(pk=self.pk)
            if featured_qs.count() >= 4:
                from django.core.exceptions import ValidationError
                raise ValidationError("Only 4 categories can be featured at a time.")

        if self.title:
            self.title = ' '.join(str(self.title).strip().split())
        if not self.slug:
            base_slug = slugify(self.title) or 'category'
            unique_slug = base_slug
            counter = 1
            while Category.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    @property
    def programmes_count(self):
        return self.courses.filter(is_deleted=False).count()

    def __str__(self):
        return self.title
