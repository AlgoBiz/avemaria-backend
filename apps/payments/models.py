import uuid
from django.db import models
from core.models import BaseModel
from core.fields import JSONDataField


class PaymentTransaction(BaseModel):
    ITEM_TYPE_CHOICES = (
        ('course', 'Course Enrollment'),
        ('resource', 'Study Resource'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='payment_transactions',
        help_text="Student who initiated the payment"
    )
    item_type = models.CharField(max_length=30, choices=ITEM_TYPE_CHOICES)
    item_id = models.PositiveIntegerField(help_text="ID of the Course or PaidResource")
    item_title = models.CharField(max_length=255, blank=True, default='')

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='gbp')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', db_index=True)

    stripe_session_id = models.CharField(max_length=255, blank=True, default='', db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, default='', db_index=True)
    stripe_customer_email = models.EmailField(blank=True, default='')

    receipt_number = models.CharField(max_length=100, blank=True, default='')
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = JSONDataField(default=dict, blank=True, help_text="Extra payload data from Stripe webhook")

    class Meta:
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f"{self.student.name} - {self.get_item_type_display()} ({self.currency.upper()} {self.amount}) - {self.status}"
