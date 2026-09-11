from django.db import models
from django.utils.text import slugify
from core.models import BaseModel

class Category(BaseModel):
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    cover_image = models.ImageField(upload_to='categories/', null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Course Category'
        verbose_name_plural = 'Course Categories'
        ordering = ['-created_at', '-id']

    def save(self, *args, **kwargs):
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
