from django.db import models
from django.utils.text import slugify
from core.models import BaseModel


class GalleryCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Gallery Category'
        verbose_name_plural = 'Gallery Categories'
        ordering = ['id']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def photos_count(self):
        return GalleryItem.objects.filter(
            models.Q(category__iexact=self.name) | models.Q(category_slug__iexact=self.slug),
            is_deleted=False
        ).count()

    def __str__(self):
        return self.name


class GalleryItem(BaseModel):
    title = models.CharField(max_length=255, blank=True, default='')
    caption = models.CharField(max_length=255, blank=True, default='')
    category = models.CharField(max_length=100, default='Laboratory')
    category_slug = models.CharField(max_length=120, blank=True, default='')
    image = models.ImageField(upload_to='gallery/')
    alt_text = models.CharField(max_length=255, blank=True, help_text="Accessibility alt text")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Campus Gallery Item'
        verbose_name_plural = 'Campus Gallery'
        ordering = ['-created_at', '-id']

    def save(self, *args, **kwargs):
        if not self.title and self.caption:
            self.title = self.caption
        elif not self.caption and self.title:
            self.caption = self.title
        if self.category and not self.category_slug:
            self.category_slug = slugify(self.category)
        super().save(*args, **kwargs)

    def __str__(self):
        display_title = self.title or self.caption or "Untitled Photo"
        return f"{display_title} ({self.category})"

