from django.db import models
from core.models import BaseModel

class Enquiry(BaseModel):
    STATUS_CHOICES = (
        ('new', 'New Lead'),
        ('contacted', 'Contacted'),
        ('resolved', 'Resolved'),
    )

    candidate_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True, null=True)
    topic = models.CharField(max_length=150, help_text="Course or discipline consulted for")
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')

    class Meta:
        verbose_name = 'Admissions Enquiry'
        verbose_name_plural = 'Admissions Enquiries'
        ordering = ['-created_at', '-id']

    @property
    def received_at(self):
        return self.created_at

    @property
    def message_snippet(self):
        return (self.message[:90] + '...') if len(self.message) > 90 else self.message

    @property
    def inquiry_subject(self):
        if ':' in self.message and '\n' not in self.message.split(':', 1)[0]:
            candidate = self.message.split(':', 1)[0].strip()
            if len(candidate) <= 100:
                return candidate
        return self.topic

    @property
    def original_message_body(self):
        if ':' in self.message and '\n' not in self.message.split(':', 1)[0]:
            parts = self.message.split(':', 1)
            if len(parts[0].strip()) <= 100:
                return parts[1].strip()
        return self.message

    def __str__(self):
        return f"{self.candidate_name} - {self.topic} ({self.get_status_display()})"
