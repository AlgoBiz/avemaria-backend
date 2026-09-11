from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from core.models import BaseModel
from core.fields import JSONDataField

class BlogCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Blog Category'
        verbose_name_plural = 'Blog Categories'
        ordering = ['-created_at', '-id']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def articles_count(self):
        return Blog.objects.filter(category=self.name, is_deleted=False).count()

    def __str__(self):
        return self.name


class Blog(BaseModel):
    CATEGORY_CHOICES = (
        ('Exam Strategy', 'Exam Strategy'),
        ('Career Pathways', 'Career Pathways'),
        ('Clinical Skills', 'Clinical Skills'),
        ('Licensing Updates', 'Licensing Updates'),
        ('Study Advice', 'Study Advice'),
        ('Licensing', 'Licensing'),
        ('Haematology', 'Haematology'),
        ('Quality', 'Quality'),
        ('Careers', 'Careers'),
        ('Postgraduate', 'Postgraduate'),
    )

    title = models.CharField(max_length=255, verbose_name="Heading (Article / Blog Title)")
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    sub_heading = models.TextField(help_text="Overview or excerpt snippet", verbose_name="Sub Heading (Overview / Excerpt)")
    category = models.CharField(max_length=100, default='Exam Strategy')
    read_time = models.CharField(max_length=50, default='8 min read')
    publish_date = models.DateField(default=timezone.localdate)
    author_name = models.CharField(max_length=120, default='Dr. Anil Mathew')
    cover_image = models.ImageField(upload_to='blogs/', null=True, blank=True)

    # Dynamic block builder: [{'id': 1, 'type': 'heading', 'content': '...'}, {'id': 2, 'type': 'paragraph', 'content': '...'}]
    content_blocks = JSONDataField(
        default=list,
        blank=True,
        help_text="List of blocks: [{'id': 1, 'type': 'heading', 'content': '...'}, {'id': 2, 'type': 'paragraph', 'content': '...'}]"
    )

    # SEO & Meta Tags
    meta_description = models.CharField(max_length=160, blank=True, null=True)
    meta_keywords = JSONDataField(default=list, blank=True)

    is_published = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'
        ordering = ['-created_at', '-id']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or 'blog-post'
            slug = base_slug
            counter = 1
            while Blog.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def content_blocks_count(self):
        return len(self.content_blocks) if isinstance(self.content_blocks, list) else 0

    @property
    def publish_date_formatted(self):
        if self.publish_date:
            day = self.publish_date.strftime('%d').lstrip('0')
            month = self.publish_date.strftime('%B')
            year = self.publish_date.strftime('%Y')
            return f"{day.zfill(2)} {month} {year}"
        return ""

    def __str__(self):
        return self.title
