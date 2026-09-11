from django.db import models
from django.utils.text import slugify
from core.models import BaseModel
from core.fields import JSONDataField

class PaidResource(BaseModel):
    CATEGORY_CHOICES = (
        ('Question Papers', 'Question Papers'),
        ('Notes', 'Notes'),
        ('Video Pack', 'Video Pack'),
        ('Exam Blueprint', 'Exam Blueprint'),
        ('Mock Test Set', 'Mock Test Set'),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Question Papers')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default='£')
    description = models.TextField()

    # Highlights (max 5)
    highlights = JSONDataField(
        default=list,
        blank=True,
        help_text="Key features / bullet points displayed on resource card"
    )

    class Meta:
        verbose_name = 'Paid Resource'
        verbose_name_plural = 'Paid Resources'
        ordering = ['-created_at', '-id']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def pdf_count(self):
        return self.pdf_files.filter(is_deleted=False).count()

    def __str__(self):
        return f"{self.title} ({self.category})"


class ResourcePDF(BaseModel):
    resource = models.ForeignKey(PaidResource, on_delete=models.CASCADE, related_name='pdf_files')
    file = models.FileField(upload_to='resources/pdfs/')
    title = models.CharField(max_length=255, blank=True)
    file_size = models.CharField(max_length=50, blank=True)

    def save(self, *args, **kwargs):
        if not self.title and self.file:
            self.title = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Resource PDF'
        verbose_name_plural = 'Resource PDFs'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f"{self.title} - {self.resource.title}"


class ResourcePurchase(BaseModel):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='purchased_resources',
        help_text="The student who purchased this resource."
    )
    resource = models.ForeignKey(
        PaidResource,
        on_delete=models.CASCADE,
        related_name='purchases',
        help_text="The purchased study resource."
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='active')
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default='paid')
    payment_method = models.CharField(max_length=50, blank=True, default='demo', help_text="e.g. demo, card, stripe, paypal")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default='£')
    order_id = models.CharField(max_length=100, blank=True, default='', help_text="Reference/Order ID for this purchase")
    purchased_at = models.DateTimeField(auto_now_add=True)

    download_count = models.PositiveIntegerField(default=0, help_text="Number of times resource was accessed/downloaded")
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    # Receipt / Invoice tracking
    receipt_number = models.CharField(max_length=100, blank=True, default='', help_text="Invoice / Receipt Number")
    receipt_emailed = models.BooleanField(default=False, help_text="Whether the receipt has been emailed to the student")
    receipt_emailed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Resource Purchase'
        verbose_name_plural = 'Resource Purchases'
        unique_together = ('student', 'resource')
        ordering = ['-purchased_at', '-id']

    def save(self, *args, **kwargs):
        if not self.receipt_number and self.order_id:
            self.receipt_number = self.order_id
        super().save(*args, **kwargs)
        if not self.receipt_number:
            self.receipt_number = f"INV-{self.id:05d}"
            ResourcePurchase.objects.filter(id=self.id).update(receipt_number=self.receipt_number)

    def __str__(self):
        return f"{self.student.name} - {self.resource.title} ({self.get_status_display()})"


