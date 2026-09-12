from django.db import models
from django.utils.text import slugify
from core.models import BaseModel
from core.fields import JSONDataField
from apps.categories.models import Category

class Course(BaseModel):
    LEVEL_CHOICES = (
        ('Beginner', 'Beginner Level'),
        ('Intermediate', 'Intermediate Level'),
        ('Advanced', 'Advanced Level'),
    )

    LEARNING_MODE_CHOICES = (
        ('live online', 'Live online'),
        ('recorded', 'Recorded'),
        ('live online+recorded', 'Live online+recorded'),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    overview_description = models.TextField(blank=True, default='', help_text="Course overview description below course name")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='courses')
    summary = models.TextField(help_text="Course summary and introduction")
    duration = models.CharField(max_length=100, default="16 weeks")
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES, default='Advanced')
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default='£')
    learning_mode = models.CharField(max_length=50, choices=LEARNING_MODE_CHOICES, default='live online+recorded')
    cover_image = models.ImageField(upload_to='courses/', null=True, blank=True)

    # 4 Highlights
    highlights = JSONDataField(
        default=list,
        blank=True,
        help_text="List of 4 structured key differentiators"
    )

    # Eligibility & Outcomes
    eligibility_criteria = JSONDataField(
        default=list,
        blank=True,
        help_text="List of eligibility requirements"
    )
    eligibility_note = models.TextField(
        blank=True,
        default='',
        help_text="Special notes or remarks for eligibility area"
    )
    course_outcomes = JSONDataField(
        default=list,
        blank=True,
        help_text="List of learning outcomes upon completion"
    )

    # Frequently Asked Questions (FAQ)
    faqs = JSONDataField(
        default=list,
        blank=True,
        help_text="Frequently asked questions list: [{'question': '...', 'answer': '...'}]"
    )

    # SEO & Meta tags
    meta_description = models.CharField(max_length=160, blank=True, null=True)
    meta_keywords = JSONDataField(
        default=list,
        blank=True,
        help_text="SEO keywords and search tags"
    )

    # Faculty details
    faculty_name = models.CharField(max_length=150, blank=True, null=True, default="Dr. Anil Mathew, PhD")
    faculty_title = models.CharField(max_length=150, blank=True, null=True, default="Clinical Biochemistry Lead")
    faculty_qualification = models.CharField(max_length=255, blank=True, default="", help_text="e.g. PhD (Clinical Biochemistry), FRCPath, HCPC Reg")
    faculty_experience = models.CharField(max_length=150, blank=True, default="", help_text="e.g. 15+ Years Clinical & Academic Experience")
    faculty_bio = models.TextField(blank=True, null=True)
    faculty_image = models.ImageField(upload_to='faculty/', null=True, blank=True)

    # Syllabus & Schedule
    curriculum = JSONDataField(
        default=list,
        blank=True,
        help_text="List of modules and syllabus topics"
    )
    weekly_session_commitment = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Weekly Session Commitment badge text, e.g. 4 sessions / week (8 hours total)"
    )
    schedule_details = models.TextField(blank=True, null=True, help_text="Schedule summary narrative")

    # Metadata & Metrics
    modules_count = models.PositiveIntegerField(default=6)
    highlights_count = models.PositiveIntegerField(default=4)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.8)
    reviews_count = models.PositiveIntegerField(default=35)
    enrolled_count = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Course / Programme'
        verbose_name_plural = 'Courses & Programmes'
        ordering = ['-created_at', '-id']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if not self.faculty_qualification and self.faculty_title:
            self.faculty_qualification = self.faculty_title
        elif not self.faculty_title and self.faculty_qualification:
            self.faculty_title = self.faculty_qualification
        if self.curriculum and isinstance(self.curriculum, list) and len(self.curriculum) > 0:
            self.modules_count = len(self.curriculum)
        if self.highlights and isinstance(self.highlights, list) and len(self.highlights) > 0:
            self.highlights_count = len(self.highlights)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.category.title})"


class CourseEnrollment(BaseModel):
    STATUS_CHOICES = (
        ('enrolled', 'Opted / Enrolled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    )

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='enrolled')
    progress_percentage = models.PositiveIntegerField(default=0, help_text="Completion percentage (0-100)")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Course Enrollment'
        verbose_name_plural = 'Course Enrollments'
        unique_together = ('student', 'course')
        ordering = ['-enrolled_at', '-id']

    def __str__(self):
        return f"{self.student.name} - {self.course.title} ({self.get_status_display()})"
