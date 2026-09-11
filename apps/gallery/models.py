from django.db import models
from core.models import BaseModel

class GalleryItem(BaseModel):
    CATEGORY_CHOICES = (
        ('Laboratory', 'Laboratory'),
        ('Classroom', 'Classroom'),
        ('Clinical', 'Clinical'),
        ('Events', 'Events'),
        ('Laboratory Workstation', 'Laboratory Workstation'),
    )

    caption = models.CharField(max_length=255)
    category = models.CharField(max_length=60, choices=CATEGORY_CHOICES, default='Laboratory')
    image = models.ImageField(upload_to='gallery/')
    alt_text = models.CharField(max_length=255, blank=True, help_text="Accessibility alt text")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Campus Gallery Item'
        verbose_name_plural = 'Campus Gallery'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f"{self.caption} ({self.category})"
