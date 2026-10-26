from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from core.models import BaseModel


class Webinar(BaseModel):
    """
    Model representing Webinars and Workshops.
    Supports scheduled events, speaker/faculty attribution, registration links,
    session timing, platform details, and cover images (file upload or URL).
    """
    TYPE_WEBINAR = 'webinar'
    TYPE_WORKSHOP = 'workshop'
    TYPE_CHOICES = (
        (TYPE_WEBINAR, 'Webinar'),
        (TYPE_WORKSHOP, 'Workshop'),
    )

    STATUS_PUBLISHED = 'published'
    STATUS_DRAFT = 'draft'
    STATUS_CHOICES = (
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_DRAFT, 'Draft'),
    )
    # Backward compatibility alias
    STATUS_PUBLISH = STATUS_PUBLISHED

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_WEBINAR,
        help_text="Event type: webinar or workshop"
    )
    title = models.CharField(
        max_length=255,
        help_text="Title of the webinar or workshop"
    )
    slug = models.SlugField(
        max_length=280,
        unique=True,
        blank=True,
        db_index=True,
        help_text="URL-friendly slug auto-generated from title"
    )
    scheduled_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date on which the event is scheduled (e.g. 2026-11-15)"
    )
    timing = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text="Event timing string, e.g. '6:00-7.30 PM IST' or '10:00 AM - 1:00 PM GMT'"
    )
    platform = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text="Delivery platform, e.g. 'Live Online (Zoom)', 'Google Meet', 'In-Person'"
    )
    speaker = models.ForeignKey(
        'faculty.Faculty',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webinars',
        help_text="Faculty member delivering the session"
    )
    registration_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="External or internal registration / join link"
    )
    summary_description = models.TextField(
        blank=True,
        default='',
        help_text="Short summary / narrative description of the webinar/workshop"
    )
    outline_agenda = models.JSONField(
        blank=True,
        default=list,
        help_text="Detailed session agenda / outline or syllabus breakdown"
    )
    cover_image = models.ImageField(
        upload_to='webinars/',
        null=True,
        blank=True,
        help_text="Uploaded cover image file"
    )
    cover_image_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="External cover image URL fallback or direct link"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        help_text="Publication status: 'published' or 'draft'"
    )

    class Meta:
        verbose_name = 'Webinar / Workshop'
        verbose_name_plural = 'Webinars & Workshops'
        ordering = ['-scheduled_date', '-created_at', '-id']

    def save(self, *args, **kwargs):
        if self.status in ['publish', 'published']:
            self.status = self.STATUS_PUBLISHED
        elif self.status in ['draft', 'unpublished']:
            self.status = self.STATUS_DRAFT

        if not self.slug:
            base_slug = slugify(self.title) or f"{self.type}-event"
            unique_slug = base_slug
            counter = 1
            while Webinar.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.type.title()}] {self.title}"

    @property
    def is_published(self):
        return self.status in [self.STATUS_PUBLISHED, 'publish']

    @property
    def is_expired(self):
        """Returns True if the scheduled date has passed (prior to today)."""
        if not self.scheduled_date:
            return False
        return self.scheduled_date < timezone.localdate()

    @property
    def event_status(self):
        """
        Returns 'expired' if the scheduled date has passed,
        'draft' if not published, or 'upcoming'.
        """
        if not self.is_published:
            return 'draft'
        if self.is_expired:
            return 'expired'
        return 'upcoming'

    @property
    def effective_cover_image(self):
        if self.cover_image:
            return self.cover_image.url
        return self.cover_image_url or None

    @property
    def speaker_info(self):
        if not self.speaker:
            return None
        return {
            'id': str(self.speaker.uuid),
            'name': self.speaker.name,
        }


# Alias for explicit clarity
WebinarWorkshop = Webinar
