import base64
import json
import logging
import urllib.request
import urllib.error
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """
    Native Django Email Backend powered by Resend HTTPS REST API.
    Bypasses all VPS / hosting provider SMTP port blocks (DigitalOcean ports 25, 465, and 587).
    """

    API_URL = "https://api.resend.com/emails"

    def __init__(self, api_key=None, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = api_key or getattr(settings, 'RESEND_API_KEY', '')

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            err_msg = (
                "RESEND_API_KEY is not configured in settings or environment. "
                "Please add RESEND_API_KEY=re_... to your .env file."
            )
            logger.error(err_msg)
            if self.fail_silently:
                return 0
            raise ValueError(err_msg)

        sent_count = 0
        for message in email_messages:
            try:
                if self._send_single_message(message):
                    sent_count += 1
            except Exception as exc:
                logger.error(f"Failed to deliver email via Resend to {message.to}: {exc}")
                if not self.fail_silently:
                    raise exc

        return sent_count

    def _send_single_message(self, message):
        # Determine from_email
        from_email = (
            getattr(settings, 'RESEND_FROM_EMAIL', None)
            or message.from_email
            or getattr(settings, 'DEFAULT_FROM_EMAIL', 'onboarding@resend.dev')
        )

        # Resend rejects unverified sender domains like @gmail.com unless a custom domain is verified
        # Fall back gracefully to RESEND_FROM_EMAIL or onboarding@resend.dev
        lower_from = from_email.lower().strip()
        if any(lower_from.endswith(dom) for dom in ['@gmail.com', '@yahoo.com', '@outlook.com', '@hotmail.com']):
            fallback_from = getattr(settings, 'RESEND_FROM_EMAIL', '') or 'onboarding@resend.dev'
            if not message.reply_to:
                message.reply_to = [from_email]
            from_email = fallback_from

        # Extract HTML alternative if present
        html_body = None
        if hasattr(message, 'alternatives') and message.alternatives:
            for content, mimetype in message.alternatives:
                if mimetype == 'text/html':
                    html_body = content
                    break

        recipients = list(message.to)
        payload = {
            "from": from_email,
            "to": recipients,
            "subject": message.subject or "",
        }

        if html_body:
            payload["html"] = html_body
            if message.body:
                payload["text"] = message.body
        else:
            payload["text"] = message.body or ""

        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)

        # Process attachments (e.g. invoice PDFs)
        if getattr(message, 'attachments', None):
            attachments_list = []
            for attachment in message.attachments:
                if isinstance(attachment, tuple):
                    filename, content, mimetype = attachment[:3]
                    content_bytes = content.encode('utf-8') if isinstance(content, str) else content
                    attachments_list.append({
                        "filename": filename,
                        "content": base64.b64encode(content_bytes).decode('ascii'),
                    })
            if attachments_list:
                payload["attachments"] = attachments_list

        req = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Avemaria-Backend/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                status_code = response.getcode()
                return 200 <= status_code < 300
        except urllib.error.HTTPError as err:
            err_body = err.read().decode('utf-8', errors='ignore')
            try:
                err_json = json.loads(err_body)
                err_msg = err_json.get('message') or err_body
            except Exception:
                err_msg = err_body
            raise RuntimeError(f"Resend API error ({err.code}): {err_msg}")

