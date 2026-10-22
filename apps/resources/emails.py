from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags


def send_purchase_receipt_email(purchase, request=None):
    """
    Sends a branded purchase receipt / tax invoice email to the student
    who made the purchase. Updates receipt_emailed and receipt_emailed_at
    fields on success.

    Args:
        purchase: ResourcePurchase instance (with related student and resource).
        request: Optional HTTP request for building absolute URIs.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    try:
        student = purchase.student
        resource = purchase.resource
        recipient_email = student.email

        if not recipient_email:
            return False

        context = {
            'student': student,
            'purchase': purchase,
            'resource': resource,
            'receipt_number': purchase.receipt_number or f"INV-{purchase.id:05d}",
            'amount_paid': purchase.amount_paid,
            'currency': purchase.currency,
            'payment_method': purchase.payment_method,
            'payment_status': purchase.payment_status,
            'purchased_at': purchase.purchased_at,
            'frontend_url': getattr(settings, 'FRONTEND_URL', ''),
        }

        html_content = render_to_string(
            'emails/student_purchase_receipt_email.html', context
        )
        try:
            text_content = render_to_string(
                'emails/student_purchase_receipt_email.txt', context
            )
        except Exception:
            text_content = strip_tags(html_content)

        subject = f"Your Purchase Receipt — {resource.title} | Avemaria"
        from_email = getattr(
            settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER
        )

        email_message = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[recipient_email],
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send(fail_silently=False)

        # Mark receipt as emailed
        purchase.receipt_emailed = True
        purchase.receipt_emailed_at = timezone.now()
        purchase.save(update_fields=['receipt_emailed', 'receipt_emailed_at'])

        return True

    except Exception:
        return False
