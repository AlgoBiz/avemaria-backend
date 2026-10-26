from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags


def send_course_enrollment_receipt_email(enrollment, request=None):
    """
    Sends a branded course enrollment confirmation & tax receipt email to the student.
    Updates receipt_emailed and receipt_emailed_at fields on success.
    """
    try:
        student = enrollment.student
        course = enrollment.course
        recipient_email = student.email

        if not recipient_email:
            return False

        context = {
            'student': student,
            'enrollment': enrollment,
            'course': course,
            'receipt_number': enrollment.receipt_number or f"CR-INV-{enrollment.id:05d}",
            'amount_paid': enrollment.amount_paid or course.fee,
            'currency': enrollment.currency or course.currency or '£',
            'payment_method': enrollment.payment_method or 'stripe',
            'payment_status': enrollment.payment_status,
            'enrolled_at': enrollment.enrolled_at,
            'frontend_url': getattr(settings, 'FRONTEND_URL', 'https://avemaria-frontend.vercel.app'),
        }

        html_content = render_to_string(
            'emails/student_course_receipt_email.html', context
        )
        try:
            text_content = render_to_string(
                'emails/student_course_receipt_email.txt', context
            )
        except Exception:
            text_content = strip_tags(html_content)

        subject = f"Enrollment Confirmed & Payment Receipt — {course.title} | Avemaria"
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

        enrollment.receipt_emailed = True
        enrollment.receipt_emailed_at = timezone.now()
        enrollment.save(update_fields=['receipt_emailed', 'receipt_emailed_at'])
        return True

    except Exception:
        return False
