from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape


DEPARTMENT_EMAIL_MAP = {
    'general': 'info@avemariacareers.uk',
    'general enquiry': 'info@avemariacareers.uk',
    'general_enquiry': 'info@avemariacareers.uk',
    'other': 'info@avemariacareers.uk',
    'general enquiry / other': 'info@avemariacareers.uk',
    'admission': 'admissions@avemariacareers.uk',
    'admissions': 'admissions@avemariacareers.uk',
    'support': 'support@avemariacareers.uk',
    'payment': 'accounts@avemariacareers.uk',
    'payments': 'accounts@avemariacareers.uk',
    'accounts': 'accounts@avemariacareers.uk',
    'billing': 'accounts@avemariacareers.uk',
    'complaint': 'complaints@avemariacareers.uk',
    'complaints': 'complaints@avemariacareers.uk',
    'privacy': 'privacy@avemariacareers.uk',
}

DEFAULT_ADMISSIONS_EMAIL = 'admissions@avemariacareers.uk'
DEFAULT_FACULTY_FALLBACK_EMAIL = 'admin@avemariacareers.uk'


def resolve_enquiry_recipient(enquiry):
    """
    Determine the destination department or faculty email for an Enquiry.
    """
    eq_type = (enquiry.enquiry_type or '').strip().lower()

    if eq_type == 'faculty':
        if enquiry.faculty and getattr(enquiry.faculty, 'email', None):
            return enquiry.faculty.email.strip()
        return DEFAULT_FACULTY_FALLBACK_EMAIL

    if eq_type in DEPARTMENT_EMAIL_MAP:
        return DEPARTMENT_EMAIL_MAP[eq_type]

    # If a faculty member was explicitly attached even without enquiry_type='faculty'
    if enquiry.faculty and getattr(enquiry.faculty, 'email', None):
        return enquiry.faculty.email.strip()

    # Fallback: check if topic itself matches a known department key
    topic_key = (enquiry.topic or '').strip().lower()
    if topic_key in DEPARTMENT_EMAIL_MAP:
        return DEPARTMENT_EMAIL_MAP[topic_key]

    return DEFAULT_ADMISSIONS_EMAIL


def send_enquiry_notification_email(enquiry):
    """
    Send an enquiry notification email to the appropriate department or faculty
    email address and record `routed_to_email` on the Enquiry instance.
    Returns True on success, False on failure (never raises so submission succeeds).
    """
    try:
        recipient_email = resolve_enquiry_recipient(enquiry)
        if not recipient_email:
            return False

        if enquiry.routed_to_email != recipient_email:
            enquiry.routed_to_email = recipient_email
            enquiry.save(update_fields=['routed_to_email'])

        enquiry_type_label = enquiry.enquiry_type or 'Course / Admissions Enquiry'
        faculty_label = enquiry.faculty_name or (enquiry.faculty.name if enquiry.faculty else '')
        subject_line = enquiry.inquiry_subject or enquiry.topic or 'New Website Enquiry'
        email_subject = f"[{enquiry_type_label}] {subject_line} — {enquiry.candidate_name}"

        lines = [
            f"New enquiry received from {enquiry.candidate_name}",
            "",
            f"Name: {enquiry.candidate_name}",
            f"Email: {enquiry.email}",
            f"Phone: {enquiry.phone or 'Not provided'}",
            f"Enquiry Type: {enquiry_type_label}",
            f"Course / Topic: {enquiry.topic}",
        ]
        if faculty_label:
            lines.append(f"Selected Faculty: {faculty_label}")
        if enquiry.custom_requirement:
            lines.append(f"Specified Requirement: {enquiry.custom_requirement}")
        lines.extend([
            f"Subject: {subject_line}",
            "",
            "Message:",
            enquiry.original_message_body or enquiry.message,
        ])
        text_content = "\n".join(lines)

        faculty_html = f"<p><strong>Selected Faculty:</strong> {escape(faculty_label)}</p>" if faculty_label else ""
        custom_req_html = (
            f"<p><strong>Specified Requirement:</strong> {escape(enquiry.custom_requirement)}</p>"
            if enquiry.custom_requirement else ""
        )
        msg_html = escape(enquiry.original_message_body or enquiry.message).replace("\n", "<br>")

        html_content = f"""
        <div style="font-family: Arial, sans-serif; color: #1f2937; line-height: 1.6;">
            <h2 style="color: #1e3a8a; margin-bottom: 12px;">New Website Enquiry</h2>
            <p><strong>Name:</strong> {escape(enquiry.candidate_name)}</p>
            <p><strong>Email:</strong> {escape(enquiry.email)}</p>
            <p><strong>Phone:</strong> {escape(enquiry.phone or 'Not provided')}</p>
            <p><strong>Enquiry Type:</strong> {escape(enquiry_type_label)}</p>
            <p><strong>Course / Topic:</strong> {escape(enquiry.topic)}</p>
            {faculty_html}
            {custom_req_html}
            <p><strong>Subject:</strong> {escape(subject_line)}</p>
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 16px 0;" />
            <p><strong>Message:</strong></p>
            <p>{msg_html}</p>
        </div>
        """

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
        email_message = EmailMultiAlternatives(
            subject=email_subject,
            body=text_content,
            from_email=from_email,
            to=[recipient_email],
            reply_to=[enquiry.email] if enquiry.email else None,
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send(fail_silently=False)
        return True
    except Exception:
        return False
