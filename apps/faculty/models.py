from django.db import models
from core.models import BaseModel


class Faculty(BaseModel):
    name = models.CharField(max_length=150, help_text="Full name of faculty member / mentor, e.g. Dr. Sarah Jenkins")
    title = models.CharField(max_length=150, blank=True, default="", help_text="Designation / Title, e.g. Clinical Biochemistry Lead")
    qualification = models.CharField(max_length=255, blank=True, default="", help_text="Academic & professional qualifications, e.g. PhD, FRCPath, HCPC Reg")
    experience = models.CharField(max_length=150, blank=True, default="", help_text="Years / description of experience, e.g. 15+ Years Clinical & Academic Experience")
    department = models.CharField(max_length=150, blank=True, default="", help_text="Department / Specialization, e.g. Biomedical Science")
    bio = models.TextField(blank=True, null=True, help_text="Full bio / profile narrative")
    image = models.ImageField(upload_to='faculty/', null=True, blank=True, help_text="Profile photo")
    email = models.EmailField(blank=True, null=True, help_text="Contact email address")
    phone = models.CharField(max_length=30, blank=True, null=True, help_text="Contact phone number")
    is_published = models.BooleanField(default=True, help_text="Whether this faculty profile is published / active")
    is_featured = models.BooleanField(default=False, help_text="Whether this faculty is featured on the home/landing page")
    display_order = models.PositiveIntegerField(default=0, help_text="Order in faculty listings (ascending)")

    class Meta:
        verbose_name = 'Faculty'
        verbose_name_plural = 'Faculties'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.faculty_display

    @property
    def faculty_display(self):
        suffix = self.qualification or self.title
        if suffix:
            return f"{self.name} ({suffix})"
        return self.name

    @property
    def initials(self):
        if not self.name:
            return ""
        parts = self.name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return parts[0][:2].upper()
