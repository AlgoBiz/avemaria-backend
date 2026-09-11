from django.db import models
from django.conf import settings
from core.models import BaseModel

class Student(BaseModel):
    STATUS_CHOICES = (
        ('verified', 'Verified Learner'),
        ('pending', 'Pending Verification'),
        ('active', 'Active on Portal'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
        null=True,
        blank=True,
        help_text="Associated user account for login access."
    )

    # Profile Photo
    avatar = models.ImageField(upload_to='students/avatars/', null=True, blank=True)

    # Personal Details
    name = models.CharField(max_length=150, verbose_name="Full Name")
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50, blank=True, default='')
    whatsapp = models.CharField(max_length=50, blank=True, default='')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True, default='')
    nationality = models.CharField(max_length=100, blank=True, default='')

    # Address Details
    address_line_1 = models.CharField(max_length=255, blank=True, default='')
    address_line_2 = models.CharField(max_length=255, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='', verbose_name="City / Town")
    state = models.CharField(max_length=100, blank=True, default='', verbose_name="State / Region")
    postal_code = models.CharField(max_length=50, blank=True, default='')
    country = models.CharField(max_length=100, blank=True, default='')

    # Academic & Professional Details
    qualification = models.CharField(max_length=150, blank=True, default='', help_text="Highest qualification e.g. BSc Medical Laboratory Technology")
    institution = models.CharField(max_length=200, blank=True, default='', help_text="University / Institution e.g. MG University")
    graduating_year = models.CharField(max_length=50, blank=True, default='', help_text="Year of graduation e.g. 2021")
    current_role = models.CharField(max_length=150, blank=True, default='', help_text="e.g. Lab Technologist")
    employer_hospital = models.CharField(max_length=200, blank=True, default='', help_text="e.g. St Marys Hospital")
    years_of_experience = models.CharField(max_length=50, blank=True, default='', help_text="e.g. 2")

    # Passport Details
    passport_number = models.CharField(max_length=100, blank=True, default='')
    country_of_issue = models.CharField(max_length=100, blank=True, default='')
    passport_expiry_date = models.DateField(null=True, blank=True)

    # General & System fields
    location = models.CharField(max_length=150, blank=True, default='', help_text="e.g. London, United Kingdom")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='active')
    registered_date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Student Learner'
        verbose_name_plural = 'Student Learners'
        ordering = ['-created_at', '-id']

    @property
    def institution_and_year(self):
        return f"{self.institution} · {self.graduating_year}"

    def __str__(self):
        return f"{self.name} ({self.qualification})"


class StudentDocument(models.Model):
    DOCUMENT_TYPES = (
        ('passport', 'Passport'),
        ('aadhar', 'Aadhar Card'),
        ('bank_passbook', 'Bank Passbook / Financial Document'),
        ('degree_certificate', 'Degree / Diploma Certificate'),
        ('transcript', 'Academic Transcript / Marksheet'),
        ('experience_letter', 'Experience Certificate / Letter'),
        ('cv', 'Curriculum Vitae (CV)'),
        ('other', 'Other Document'),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES, default='other')
    title = models.CharField(max_length=200, blank=True, default='')
    file = models.FileField(upload_to='students/documents/', help_text="Accepts images (JPG, PNG, WEBP) and documents (PDF, DOC, DOCX)")
    file_name = models.CharField(max_length=255, blank=True, default='')
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="File size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Student Document'
        verbose_name_plural = 'Student Documents'
        ordering = ['-uploaded_at', '-id']

    def save(self, *args, **kwargs):
        if self.file and not self.file_name:
            import os
            self.file_name = os.path.basename(self.file.name)
        if self.file and hasattr(self.file, 'size') and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.student.name} ({self.file_name})"
