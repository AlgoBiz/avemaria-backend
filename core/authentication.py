from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class SafeJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication class that safely ignores invalid, expired, or malformed
    tokens on public endpoints instead of abruptly returning 401 Unauthorized.

    - If a valid JWT token is provided: authenticates the user normally.
    - If no token is provided, or the token is invalid/expired/'undefined'/'null':
      returns None (treats request as unauthenticated / AnonymousUser).

    Protected endpoints (IsAuthenticated) still enforce authentication and
    return 401 Unauthorized, while public endpoints (AllowAny) will successfully
    serve content without being blocked by stale frontend tokens.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        # Check for bad header values commonly sent by JS frontends like 'Bearer undefined' or 'Bearer null'
        try:
            raw_header = header.decode('utf-8').strip()
            parts = raw_header.split()
            if len(parts) == 2 and parts[1].lower() in ('undefined', 'null', 'none', ''):
                return None
        except Exception:
            return None

        try:
            auth_res = super().authenticate(request)
            if auth_res is not None:
                user, token = auth_res
                student = getattr(user, 'student_profile', None)
                if not student and getattr(user, 'email', None):
                    from apps.students.models import Student
                    student = Student.objects.filter(email__iexact=user.email, is_deleted=False).first()
                if student and getattr(student, 'is_suspended', False):
                    reason = student.suspension_reason or "Your account has been suspended. Please contact the administrator for assistance."
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied({"detail": reason})
            return auth_res
        except (InvalidToken, AuthenticationFailed):
            # Gracefully treat invalid / expired tokens as unauthenticated (AnonymousUser)
            return None


class SafeJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'core.authentication.SafeJWTAuthentication'
    name = 'jwtAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
