import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.db.models import Q, Sum
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse


from apps.accounts.models import User, PasswordResetOTP
from apps.students.models import Student, StudentDocument
from apps.courses.models import Course, CourseEnrollment
from apps.resources.models import PaidResource, ResourcePurchase
from apps.resources.emails import send_purchase_receipt_email
from api.v1.courses.serializers import CourseEnrollmentSerializer
from api.v1.resources.serializers import (
    ResourcePurchaseSerializer,
    StudentPurchaseHistorySerializer,
    StudentPaymentDetailItemSerializer,
    StudentReceiptSerializer,
)
from .serializers import (
    AdminProfileSerializer,
    AdminProfileUpdateSerializer,
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetValidateTokenSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    OTPPasswordResetConfirmSerializer,
    StudentRegisterSerializer,
    StudentLoginSerializer,
    StudentProfileSerializer,
    StudentDocumentSerializer,
    AdminLoginSerializer,
    AdminLoginResponseSerializer,
    StudentChangePasswordSerializer,
    StudentLogoutSerializer,
    MessageResponseSerializer,
    PasswordResetRequestResponseSerializer,
    PasswordResetValidateResponseSerializer,
    OTPRequestResponseSerializer,
    OTPVerifyResponseSerializer,
    StudentDocumentUploadSerializer,
    StudentDocumentUploadResponseSerializer,
    StudentCourseEnrollSerializer,
    StudentCourseEnrollResponseSerializer,
    StudentCoursesListResponseSerializer,
    StudentResourcePurchaseSerializer,
    StudentResourcePurchaseResponseSerializer,
    StudentResourceAccessResponseSerializer,
    StudentPurchasedResourcesListResponseSerializer,
    StudentPurchaseHistoryListResponseSerializer,
    StudentPaymentDetailsResponseSerializer,
    StudentReceiptsListResponseSerializer,
    StudentReceiptResendResponseSerializer,
)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'display_name': self.user.display_name,
            'role': self.user.role,
        }
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class AdminProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AdminProfileSerializer

    @extend_schema(
        tags=['Admin Profile'],
        summary="Get Current Admin Profile",
        description="Retrieves the profile details of the authenticated administrator.",
        responses={200: AdminProfileSerializer}
    )
    def get(self, request):
        serializer = AdminProfileSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        tags=['Admin Profile'],
        summary="Update Current Admin Profile (PUT)",
        description="Updates display name, email, or avatar of the authenticated administrator.",
        request=AdminProfileUpdateSerializer,
        responses={200: AdminProfileSerializer, 400: OpenApiResponse(description="Validation error")}
    )
    def put(self, request):
        serializer = AdminProfileUpdateSerializer(instance=request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(AdminProfileSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Admin Profile'],
        summary="Partially Update Current Admin Profile (PATCH)",
        description="Partially updates administrator details.",
        request=AdminProfileUpdateSerializer,
        responses={200: AdminProfileSerializer, 400: OpenApiResponse(description="Validation error")}
    )
    def patch(self, request):
        return self.put(request)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    @extend_schema(
        tags=['Admin Authentication'],
        summary="Change Administrator Password",
        description="Allows an authenticated administrator to update their password.",
        request=ChangePasswordSerializer,
        responses={
            200: MessageResponseSerializer,
            400: OpenApiResponse(description="Validation error")
        }
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    """
    Initiates the password reset workflow by generating a secure single-use token
    and delivering an Avemaria brand-styled HTML email to the administrator.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(
        tags=['Admin Authentication'],
        summary="Request Admin Password Reset Link",
        description="Generates a single-use token and emails password reset link to administrator.",
        request=PasswordResetRequestSerializer,
        responses={
            200: PasswordResetRequestResponseSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Account not found")
        }
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].strip().lower()
        custom_frontend_url = serializer.validated_data.get('frontend_url', '').strip()

        # Resolve frontend base URL (dynamic or from settings)
        base_url = (custom_frontend_url or getattr(settings, 'FRONTEND_URL', 'https://avemaria-frontend.vercel.app')).rstrip('/')

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return Response(
                {"detail": "No active admin account found with this email address."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate single-use cryptographic token and base64 encoded user ID
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = f"{base_url}/admin/reset-password?uid={uid}&token={token}"

        valid_hours = getattr(settings, 'PASSWORD_RESET_TIMEOUT', 86400) // 3600

        context = {
            'user': user,
            'reset_url': reset_url,
            'valid_hours': valid_hours,
        }

        try:
            html_content = render_to_string('emails/admin_password_reset.html', context)
            text_content = render_to_string('emails/admin_password_reset.txt', context)

            subject = "Reset Your Admin Password — Avemaria Admin Portal"
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)

            email_message = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[user.email],
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send(fail_silently=False)

        except Exception as exc:
            return Response(
                {"detail": f"Failed to send email: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "status": "success",
                "message": f"A password reset link has been dispatched to {user.email}.",
                "email": user.email,
                "valid_hours": valid_hours
            },
            status=status.HTTP_200_OK
        )


class PasswordResetValidateTokenView(APIView):
    """
    Validates whether the token and UID are valid and non-expired.
    Useful for the frontend to show a warning or load the form immediately.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetValidateTokenSerializer

    @extend_schema(
        tags=['Admin Authentication'],
        summary="Validate Password Reset Token",
        description="Validates whether the token and UID are valid and non-expired.",
        request=PasswordResetValidateTokenSerializer,
        responses={
            200: PasswordResetValidateResponseSerializer,
            400: OpenApiResponse(description="Invalid or expired token")
        }
    )
    def post(self, request):
        serializer = PasswordResetValidateTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uid_b64 = serializer.validated_data['uid']
        token = serializer.validated_data['token']

        try:
            uid = force_str(urlsafe_base64_decode(uid_b64))
            user = User.objects.get(pk=uid, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if not user or not default_token_generator.check_token(user, token):
            return Response(
                {
                    "valid": False,
                    "detail": "The password reset link is invalid or has expired. Please request a new one."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "valid": True,
                "email": user.email,
                "display_name": user.display_name,
            },
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    """
    Applies the new password for the administrator once the token is validated.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(
        tags=['Admin Authentication'],
        summary="Confirm Admin Password Reset",
        description="Sets the new password using the validated UID and token.",
        request=PasswordResetConfirmSerializer,
        responses={
            200: MessageResponseSerializer,
            400: OpenApiResponse(description="Validation error or invalid token")
        }
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uid_b64 = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            uid = force_str(urlsafe_base64_decode(uid_b64))
            user = User.objects.get(pk=uid, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if not user or not default_token_generator.check_token(user, token):
            return Response(
                {
                    "detail": "The password reset link is invalid or has expired. Please request a new one."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {
                "status": "success",
                "message": "Your password has been successfully reset. You can now log in with your new password."
            },
            status=status.HTTP_200_OK
        )


class OTPRequestView(APIView):
    """
    Initiates 6-digit cryptographic OTP generation with strict 60-second validity
    and cooldown protection to prevent rapid spamming.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = OTPRequestSerializer

    @extend_schema(
        tags=['Admin Authentication'],
        summary="Request 6-digit OTP Code",
        description="Dispatches a 6-digit OTP to the admin's email with 60s validity and cooldown.",
        request=OTPRequestSerializer,
        responses={
            200: OTPRequestResponseSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Account not found"),
            429: OpenApiResponse(description="Cooldown active")
        }
    )
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return Response(
                {"detail": "No active admin account found with this email address."},
                status=status.HTTP_404_NOT_FOUND
            )

        now = timezone.now()

        # Cooldown check: prevent requesting if an active (unexpired, unused, attempts < 5) OTP exists
        latest_active_otp = PasswordResetOTP.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=now,
            attempts__lt=5
        ).order_by('-created_at').first()

        if latest_active_otp:
            remaining_seconds = int((latest_active_otp.expires_at - now).total_seconds())
            if remaining_seconds > 0:
                return Response(
                    {
                        "detail": f"An active verification code has already been sent. Please wait {remaining_seconds} seconds before requesting a new code.",
                        "cooldown_remaining": remaining_seconds
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

        # Invalidate any prior active OTPs for this user
        PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)

        # Generate cryptographic 6-digit OTP
        otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
        expires_at = now + timedelta(seconds=60)

        otp_record = PasswordResetOTP.objects.create(
            user=user,
            otp=otp_code,
            expires_at=expires_at
        )

        # Send styled OTP email
        context = {
            'user': user,
            'otp': otp_code,
            'expires_seconds': 60,
        }

        try:
            html_content = render_to_string('emails/admin_otp_email.html', context)
            text_content = render_to_string('emails/admin_otp_email.txt', context)

            subject = f"{otp_code} is your Avemaria Admin Verification Code"
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)

            email_message = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[user.email],
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send(fail_silently=False)

        except Exception as exc:
            # If email fails, delete the created OTP record so user isn't locked out by cooldown
            otp_record.delete()
            return Response(
                {"detail": f"Failed to deliver verification email: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "status": "success",
                "message": f"A 6-digit verification code has been dispatched to {user.email}.",
                "email": user.email,
                "expires_in": 60
            },
            status=status.HTTP_200_OK
        )


class OTPVerifyView(APIView):
    """
    Verifies the 6-digit OTP. Enforces max 5 consecutive attempts and 60s expiration.
    Returns a signed reset token valid for completing the password reset.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = OTPVerifySerializer

    @extend_schema(
        tags=['Admin Authentication'],
        summary="Verify Admin OTP Code",
        description="Verifies the submitted 6-digit OTP and returns a signed reset token.",
        request=OTPVerifySerializer,
        responses={
            200: OTPVerifyResponseSerializer,
            400: OpenApiResponse(description="Invalid or expired OTP")
        }
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].strip().lower()
        submitted_otp = serializer.validated_data['otp'].strip()

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return Response(
                {"detail": "No active admin account found with this email address."},
                status=status.HTTP_404_NOT_FOUND
            )

        otp_record = PasswordResetOTP.objects.filter(user=user).order_by('-created_at').first()
        if not otp_record:
            return Response(
                {"detail": "No verification code requested. Please request an OTP first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_record.is_used:
            return Response(
                {"detail": "This verification code has already been used. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_record.attempts >= 5:
            return Response(
                {
                    "detail": "This verification code has been disabled due to reaching the maximum 5 consecutive failed attempts. Please request a new one.",
                    "attempts_remaining": 0
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_record.is_expired():
            return Response(
                {"detail": "This verification code has expired (60s limit). Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate code match
        if otp_record.otp != submitted_otp:
            otp_record.attempts += 1
            otp_record.save(update_fields=['attempts'])
            remaining = 5 - otp_record.attempts
            if remaining <= 0:
                return Response(
                    {
                        "detail": "Invalid verification code. You have reached the maximum 5 consecutive attempts. This OTP is now permanently disabled.",
                        "attempts_remaining": 0
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {
                    "detail": f"Invalid verification code. You have {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
                    "attempts_remaining": remaining
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Success - generate temporary cryptographic reset token
        signer = TimestampSigner(salt='password-reset-otp')
        reset_token = signer.sign(f"{user.id}:{otp_record.id}")

        return Response(
            {
                "valid": True,
                "message": "OTP verified successfully.",
                "reset_token": reset_token,
                "email": user.email
            },
            status=status.HTTP_200_OK
        )


class OTPPasswordResetConfirmView(APIView):
    """
    Confirms password reset via either:
    1. Two-step flow: Using the signed `reset_token` obtained from OTPVerifyView.
    2. Direct flow: Submitting `email` + `otp` + `new_password` directly.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = OTPPasswordResetConfirmSerializer

    @extend_schema(
        tags=['Admin Authentication'],
        summary="Confirm Password Reset via OTP or Token",
        description="Resets the password using either signed reset_token or direct OTP verification.",
        request=OTPPasswordResetConfirmSerializer,
        responses={
            200: MessageResponseSerializer,
            400: OpenApiResponse(description="Invalid or expired credentials")
        }
    )
    def post(self, request):
        serializer = OTPPasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].strip().lower()
        new_password = serializer.validated_data['new_password']
        reset_token = serializer.validated_data.get('reset_token', '').strip()
        submitted_otp = serializer.validated_data.get('otp', '').strip()

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return Response(
                {"detail": "No active admin account found with this email address."},
                status=status.HTTP_404_NOT_FOUND
            )

        otp_record = None

        if reset_token:
            signer = TimestampSigner(salt='password-reset-otp')
            try:
                unsigned_val = signer.unsign(reset_token, max_age=600)  # 10 minutes to complete reset
                user_id_str, otp_id_str = unsigned_val.split(':')
                if int(user_id_str) != user.id:
                    raise ValueError("User mismatch")
                otp_record = PasswordResetOTP.objects.get(id=int(otp_id_str), user=user)
                if otp_record.is_used:
                    return Response(
                        {"detail": "This verification code has already been used to reset a password."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (SignatureExpired, BadSignature, ValueError, PasswordResetOTP.DoesNotExist):
                return Response(
                    {"detail": "Invalid or expired reset token. Please restart the password reset process."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        elif submitted_otp:
            otp_record = PasswordResetOTP.objects.filter(user=user).order_by('-created_at').first()
            if not otp_record:
                return Response(
                    {"detail": "No verification code found. Please request an OTP first."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if otp_record.is_used:
                return Response(
                    {"detail": "This verification code has already been used. Please request a new one."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if otp_record.attempts >= 5:
                return Response(
                    {
                        "detail": "This verification code has been disabled due to reaching the maximum 5 consecutive failed attempts. Please request a new one.",
                        "attempts_remaining": 0
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            if otp_record.is_expired():
                return Response(
                    {"detail": "This verification code has expired (60s limit). Please request a new one."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if otp_record.otp != submitted_otp:
                otp_record.attempts += 1
                otp_record.save(update_fields=['attempts'])
                remaining = 5 - otp_record.attempts
                if remaining <= 0:
                    return Response(
                        {
                            "detail": "Invalid verification code. You have reached the maximum 5 consecutive attempts. This OTP is now permanently disabled.",
                            "attempts_remaining": 0
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                return Response(
                    {
                        "detail": f"Invalid verification code. You have {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
                        "attempts_remaining": remaining
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        if not otp_record:
            return Response(
                {"detail": "Unable to verify credentials. Please provide a valid OTP or reset token."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset password and mark OTP as used
        user.set_password(new_password)
        user.save()

        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])

        return Response(
            {
                "status": "success",
                "message": "Your password has been successfully reset. You can now log in with your new password."
            },
            status=status.HTTP_200_OK
        )


class StudentRegisterView(APIView):
    """
    Public student self-registration endpoint matching the Avemaria portal
    'Create your account' form (Full name, Email address, Password).
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = StudentRegisterSerializer

    @extend_schema(
        tags=['Student Authentication'],
        summary="Student Registration (Create Account)",
        description="Registers a new student learner account and creates an active student profile with JWT session credentials.",
        request=StudentRegisterSerializer,
        responses={
            201: OpenApiResponse(description="Student registered successfully and JWT tokens returned"),
            400: OpenApiResponse(description="Validation Error")
        },
        examples=[
            OpenApiExample(
                'Student Register Request Example',
                value={
                    "full_name": "Ann Maria Joseph",
                    "email": "demo@avemaria.test",
                    "password": "Password123!",
                    "phone": "+44 7700 900123",
                    "qualification": "BSc Medical Laboratory Technology",
                    "institution": "MG University",
                    "graduating_year": "2021",
                    "location": "London, United Kingdom"
                },
                request_only=True,
                media_type='application/json'
            ),
            OpenApiExample(
                'Student Register Response Example',
                value={
                    "status": "success",
                    "message": "Your account has been created successfully.",
                    "access": "<jwt_access_token>",
                    "refresh": "<jwt_refresh_token>",
                    "user": {
                        "id": 1,
                        "email": "demo@avemaria.test",
                        "name": "Ann Maria Joseph",
                        "role": "student"
                    },
                    "student_profile": {
                        "id": 1,
                        "full_name": "Ann Maria Joseph",
                        "email": "demo@avemaria.test",
                        "phone": "+44 7700 900123",
                        "highest_qualification": "BSc Medical Laboratory Technology",
                        "university": "MG University",
                        "status": "active"
                    }
                },
                response_only=True,
                media_type='application/json'
            )
        ]
    )
    def post(self, request):
        serializer = StudentRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        full_name = serializer.validated_data['resolved_name']

        # Create user account with student role
        user = User.objects.create_user(
            email=email,
            password=password,
            display_name=full_name,
            role='student',
            is_staff=False
        )

        # Create or link student profile
        student, _ = Student.objects.update_or_create(
            email=email,
            defaults={
                'user': user,
                'name': full_name,
                'phone': serializer.validated_data.get('phone', ''),
                'qualification': serializer.validated_data.get('qualification', ''),
                'institution': serializer.validated_data.get('institution', ''),
                'graduating_year': serializer.validated_data.get('graduating_year', ''),
                'location': serializer.validated_data.get('location', ''),
                'status': 'active',
            }
        )

        # Generate JWT session tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "status": "success",
                "message": "Your account has been created successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.display_name,
                    "role": user.role,
                },
                "student_profile": StudentProfileSerializer(student, context={'request': request}).data
            },
            status=status.HTTP_201_CREATED
        )


class StudentLoginView(APIView):
    """
    Public student sign-in endpoint matching the Avemaria portal
    'Sign in to your account' form (Email address, Password).
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = StudentLoginSerializer

    @extend_schema(
        tags=['Student Authentication'],
        summary="Student Login (Sign In)",
        description="Authenticates a student by email and password, returning JWT access & refresh tokens along with user and profile data.",
        request=StudentLoginSerializer,
        responses={
            200: OpenApiResponse(description="Signed in successfully with JWT session tokens"),
            400: OpenApiResponse(description="Invalid email address or password")
        },
        examples=[
            OpenApiExample(
                'Student Login Request Example',
                value={
                    "email": "demo@avemaria.test",
                    "password": "Password123!"
                },
                request_only=True,
                media_type='application/json'
            ),
            OpenApiExample(
                'Student Login Response Example',
                value={
                    "status": "success",
                    "message": "Signed in successfully.",
                    "access": "<jwt_access_token>",
                    "refresh": "<jwt_refresh_token>",
                    "user": {
                        "id": 1,
                        "email": "demo@avemaria.test",
                        "name": "Ann Maria Joseph",
                        "role": "student"
                    },
                    "student_profile": {
                        "id": 1,
                        "full_name": "Ann Maria Joseph",
                        "email": "demo@avemaria.test",
                        "phone": "+44 7700 900123",
                        "highest_qualification": "BSc Medical Laboratory Technology",
                        "university": "MG University",
                        "status": "active"
                    }
                },
                response_only=True,
                media_type='application/json'
            )
        ]
    )
    def post(self, request):
        serializer = StudentLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].strip().lower()
        password = serializer.validated_data['password']

        user = User.objects.filter(email__iexact=email).first()
        if not user or not user.check_password(password):
            return Response(
                {"detail": "Invalid email address or password. Please try again."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.is_active or user.is_deleted:
            return Response(
                {"detail": "This account is inactive. Please contact Avemaria support."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retrieve or link Student profile
        student = getattr(user, 'student_profile', None)
        if not student:
            student = Student.objects.filter(email__iexact=user.email).first()
            if student:
                student.user = user
                student.save(update_fields=['user'])
            else:
                student = Student.objects.create(
                    user=user,
                    name=user.display_name,
                    email=user.email,
                    status='active'
                )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "status": "success",
                "message": "Signed in successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.display_name,
                    "role": user.role,
                },
                "student_profile": StudentProfileSerializer(student, context={'request': request}).data
            },
            status=status.HTTP_200_OK
        )


class StudentProfileView(APIView):
    """
    Retrieves or updates the authenticated student's profile information.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentProfileSerializer

    @extend_schema(
        tags=['Student Portal & Profile'],
        summary="Retrieve authenticated student profile",
        description="Retrieves the full profile details of the authenticated student, including personal details, address, academic background, passport info, and uploaded documents.",
        responses={
            200: StudentProfileSerializer,
        },
        examples=[
            OpenApiExample(
                'Student Profile Response Example',
                value={
                    "id": 1,
                    "avatar": "http://127.0.0.1:8000/media/students/avatars/profile.jpg",
                    "avatar_url": "http://127.0.0.1:8000/media/students/avatars/profile.jpg",
                    "name": "Ann Maria Joseph",
                    "full_name": "Ann Maria Joseph",
                    "email": "demo@avemaria.test",
                    "phone": "+44 7700 900123",
                    "whatsapp": "+44 7700 900123",
                    "date_of_birth": "1999-12-04",
                    "dob": "1999-12-04",
                    "gender": "Female",
                    "nationality": "Indian",
                    "address_line_1": "Flat 4, 22 Shelton Street",
                    "address_line_2": "",
                    "city": "London",
                    "state": "Greater London",
                    "postal_code": "WC2H 9JQ",
                    "country": "United Kingdom",
                    "qualification": "BSc Medical Laboratory Technology",
                    "highest_qualification": "BSc Medical Laboratory Technology",
                    "institution": "MG University",
                    "university": "MG University",
                    "graduating_year": "2021",
                    "year_of_graduation": "2021",
                    "institution_and_year": "MG University · 2021",
                    "current_role": "Lab Technologist",
                    "employer_hospital": "St Marys Hospital",
                    "years_of_experience": "2",
                    "passport_number": "P12345678",
                    "country_of_issue": "India",
                    "passport_expiry_date": "2029-08-15",
                    "expiry_date": "2029-08-15",
                    "passport_expiry": "2029-08-15",
                    "documents": [],
                    "location": "London, United Kingdom",
                    "status": "active",
                    "status_display": "Active on Portal",
                    "registered_date": "2026-09-12",
                    "created_at": "2026-09-12T10:00:00Z",
                    "updated_at": "2026-09-12T10:30:00Z"
                },
                response_only=True,
                media_type='application/json'
            )
        ]
    )
    def get(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            student, _ = Student.objects.get_or_create(
                email=request.user.email,
                defaults={'user': request.user, 'name': request.user.display_name, 'status': 'active'}
            )
        if student.user != request.user:
            student.user = request.user
            student.save(update_fields=['user'])

        return Response(StudentProfileSerializer(student, context={'request': request}).data)

    @extend_schema(
        tags=['Student Portal & Profile'],
        summary="Save student profile via POST (or Multipart Avatar upload)",
        description="Allows saving student profile fields or uploading profile photo/avatar using POST.",
        request=StudentProfileSerializer,
        responses={
            200: StudentProfileSerializer,
            400: OpenApiResponse(description="Validation Error")
        },
        examples=[
            OpenApiExample(
                'Student Profile Save Example (application/json)',
                value={
                    "full_name": "Ann Maria Joseph",
                    "phone": "+44 7700 900123",
                    "whatsapp": "+44 7700 900123",
                    "date_of_birth": "1999-12-04",
                    "gender": "Female",
                    "nationality": "Indian",
                    "address_line_1": "Flat 4, 22 Shelton Street",
                    "address_line_2": "",
                    "city": "London",
                    "state": "Greater London",
                    "postal_code": "WC2H 9JQ",
                    "country": "United Kingdom",
                    "highest_qualification": "BSc Medical Laboratory Technology",
                    "university": "MG University",
                    "year_of_graduation": "2021",
                    "current_role": "Lab Technologist",
                    "employer_hospital": "St Marys Hospital",
                    "years_of_experience": "2",
                    "passport_number": "P12345678",
                    "country_of_issue": "India",
                    "expiry_date": "2029-08-15"
                },
                request_only=True,
                media_type='application/json'
            )
        ]
    )
    def post(self, request):
        """Allow saving/updating profile via POST as well as PATCH/PUT."""
        return self.patch(request)

    @extend_schema(
        tags=['Student Portal & Profile'],
        summary="Full update of student profile (PUT)",
        description="Replaces or updates student profile attributes with full payload.",
        request=StudentProfileSerializer,
        responses={
            200: StudentProfileSerializer,
            400: OpenApiResponse(description="Validation Error")
        },
        examples=[
            OpenApiExample(
                'Student Profile Update Example (application/json)',
                value={
                    "full_name": "Ann Maria Joseph",
                    "phone": "+44 7700 900123",
                    "whatsapp": "+44 7700 900123",
                    "date_of_birth": "1999-12-04",
                    "gender": "Female",
                    "nationality": "Indian",
                    "address_line_1": "Flat 4, 22 Shelton Street",
                    "address_line_2": "",
                    "city": "London",
                    "state": "Greater London",
                    "postal_code": "WC2H 9JQ",
                    "country": "United Kingdom",
                    "highest_qualification": "BSc Medical Laboratory Technology",
                    "university": "MG University",
                    "year_of_graduation": "2021",
                    "current_role": "Lab Technologist",
                    "employer_hospital": "St Marys Hospital",
                    "years_of_experience": "2",
                    "passport_number": "P12345678",
                    "country_of_issue": "India",
                    "expiry_date": "2029-08-15"
                },
                request_only=True,
                media_type='application/json'
            )
        ]
    )
    def put(self, request):
        return self.patch(request)

    @extend_schema(
        tags=['Student Portal & Profile'],
        summary="Save / Update student profile (PATCH)",
        description="Saves and partially updates the student's profile details. Accepts personal details, address, academic credentials, and passport details. Also supports profile photo uploads.",
        request=StudentProfileSerializer,
        responses={
            200: StudentProfileSerializer,
            400: OpenApiResponse(description="Validation Error")
        },
        examples=[
            OpenApiExample(
                'Save Profile Request Example (application/json)',
                value={
                    "full_name": "Ann Maria Joseph",
                    "phone": "+44 7700 900123",
                    "whatsapp": "+44 7700 900123",
                    "date_of_birth": "1999-12-04",
                    "gender": "Female",
                    "nationality": "Indian",
                    "address_line_1": "Flat 4, 22 Shelton Street",
                    "address_line_2": "",
                    "city": "London",
                    "state": "Greater London",
                    "postal_code": "WC2H 9JQ",
                    "country": "United Kingdom",
                    "highest_qualification": "BSc Medical Laboratory Technology",
                    "university": "MG University",
                    "year_of_graduation": "2021",
                    "current_role": "Lab Technologist",
                    "employer_hospital": "St Marys Hospital",
                    "years_of_experience": "2",
                    "passport_number": "P12345678",
                    "country_of_issue": "India",
                    "expiry_date": "2029-08-15"
                },
                request_only=True,
                media_type='application/json'
            ),
            OpenApiExample(
                'Save Profile Response Example (application/json)',
                value={
                    "id": 1,
                    "avatar": "http://127.0.0.1:8000/media/students/avatars/profile.jpg",
                    "avatar_url": "http://127.0.0.1:8000/media/students/avatars/profile.jpg",
                    "name": "Ann Maria Joseph",
                    "full_name": "Ann Maria Joseph",
                    "email": "demo@avemaria.test",
                    "phone": "+44 7700 900123",
                    "whatsapp": "+44 7700 900123",
                    "date_of_birth": "1999-12-04",
                    "dob": "1999-12-04",
                    "gender": "Female",
                    "nationality": "Indian",
                    "address_line_1": "Flat 4, 22 Shelton Street",
                    "address_line_2": "",
                    "city": "London",
                    "state": "Greater London",
                    "postal_code": "WC2H 9JQ",
                    "country": "United Kingdom",
                    "qualification": "BSc Medical Laboratory Technology",
                    "highest_qualification": "BSc Medical Laboratory Technology",
                    "institution": "MG University",
                    "university": "MG University",
                    "graduating_year": "2021",
                    "year_of_graduation": "2021",
                    "institution_and_year": "MG University · 2021",
                    "current_role": "Lab Technologist",
                    "employer_hospital": "St Marys Hospital",
                    "years_of_experience": "2",
                    "passport_number": "P12345678",
                    "country_of_issue": "India",
                    "passport_expiry_date": "2029-08-15",
                    "expiry_date": "2029-08-15",
                    "passport_expiry": "2029-08-15",
                    "documents": [],
                    "location": "London, United Kingdom",
                    "status": "active",
                    "status_display": "Active on Portal",
                    "registered_date": "2026-09-12",
                    "created_at": "2026-09-12T10:00:00Z",
                    "updated_at": "2026-09-12T10:30:00Z"
                },
                response_only=True,
                media_type='application/json'
            )
        ]
    )
    def patch(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            student, _ = Student.objects.get_or_create(
                email=request.user.email,
                defaults={'user': request.user, 'name': request.user.display_name, 'status': 'active'}
            )
        if student.user != request.user:
            student.user = request.user
            student.save(update_fields=['user'])

        serializer = StudentProfileSerializer(student, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()

            # Handle Profile Photo upload flexibly (avatar / photo / profile_photo / image)
            photo_file = (
                request.FILES.get('avatar') or
                request.FILES.get('photo') or
                request.FILES.get('profile_photo') or
                request.FILES.get('image')
            )
            if photo_file:
                student.avatar = photo_file
                student.save(update_fields=['avatar'])
                if hasattr(request.user, 'avatar') and hasattr(request.user, 'save'):
                    request.user.avatar = photo_file
                    request.user.save(update_fields=['avatar'])

            # Handle multiple documents uploaded under 'documents' or 'files'
            doc_files = request.FILES.getlist('documents') or request.FILES.getlist('files')
            for f in doc_files:
                StudentDocument.objects.create(
                    student=student,
                    file=f,
                    title=f.name,
                    document_type='other'
                )

            # Handle named document uploads (passport, aadhar, bank passbook, etc.)
            named_mappings = {
                'passport_file': ('passport', 'Passport'),
                'passport_document': ('passport', 'Passport'),
                'aadhar_file': ('aadhar', 'Aadhar Card'),
                'aadhar_document': ('aadhar', 'Aadhar Card'),
                'bank_passbook_file': ('bank_passbook', 'Bank Passbook / Financial Statement'),
                'bank_passbook_document': ('bank_passbook', 'Bank Passbook / Financial Statement'),
                'degree_certificate_file': ('degree_certificate', 'Degree / Diploma Certificate'),
                'cv_file': ('cv', 'Curriculum Vitae (CV)'),
            }
            for field_key, (doc_type, default_title) in named_mappings.items():
                if field_key in request.FILES:
                    f = request.FILES[field_key]
                    StudentDocument.objects.create(
                        student=student,
                        file=f,
                        title=default_title,
                        document_type=doc_type
                    )

            # If name was updated, synchronize User display_name
            if 'name' in serializer.validated_data and serializer.validated_data['name']:
                request.user.display_name = serializer.validated_data['name']
                request.user.save(update_fields=['display_name'])

            refreshed = StudentProfileSerializer(student, context={'request': request}).data
            return Response(refreshed, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentDocumentUploadView(APIView):
    """
    Dedicated endpoint for students to upload individual documents
    (Passport, Aadhar, Bank Passbook, Certificates, etc.).
    Supports both image formats (JPG, PNG, WEBP) and documents (PDF, DOC, DOCX).
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentDocumentUploadSerializer

    @extend_schema(
        tags=['Student Documents'],
        summary="Upload Student Document",
        description="Uploads a passport, certificate, ID card, or other verification file for the student profile.",
        request=StudentDocumentUploadSerializer,
        responses={
            201: StudentDocumentUploadResponseSerializer,
            400: OpenApiResponse(description="No file provided or validation error")
        }
    )
    def post(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            student, _ = Student.objects.get_or_create(
                email=request.user.email,
                defaults={'user': request.user, 'name': request.user.display_name, 'status': 'active'}
            )

        file = request.FILES.get('file') or request.FILES.get('document')
        if not file:
            return Response(
                {"detail": "No file uploaded. Please attach a file in multipart/form-data."},
                status=status.HTTP_400_BAD_REQUEST
            )

        document_type = request.data.get('document_type', 'other').strip().lower()
        title = request.data.get('title', '').strip() or file.name

        doc = StudentDocument.objects.create(
            student=student,
            file=file,
            document_type=document_type,
            title=title
        )

        return Response(
            {
                "status": "success",
                "message": f"Document '{title}' uploaded successfully.",
                "document": StudentDocumentSerializer(doc, context={'request': request}).data
            },
            status=status.HTTP_201_CREATED
        )


class StudentDocumentDeleteView(APIView):
    """
    Allows a student to delete an uploaded document from their profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Student Documents'],
        summary="Delete Uploaded Student Document",
        description="Removes an uploaded document from the student's profile.",
        responses={
            200: MessageResponseSerializer,
            404: OpenApiResponse(description="Document not found")
        }
    )
    def delete(self, request, pk):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        doc = StudentDocument.objects.filter(student=student, pk=pk).first()
        if not doc:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        doc.file.delete(save=False)
        doc.delete()

        return Response(
            {"status": "success", "message": "Document deleted successfully."},
            status=status.HTTP_200_OK
        )


class AdminLoginView(APIView):
    """
    Dedicated administrator login endpoint. Enforces strict role verification
    and blocks non-admin (e.g. student) accounts with 403 Forbidden.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = AdminLoginSerializer

    @extend_schema(
        tags=['Admin Authentication'],
        summary="Administrator Login",
        description="Authenticates administrator credentials and returns JWT session tokens.",
        request=AdminLoginSerializer,
        responses={
            200: AdminLoginResponseSerializer,
            400: OpenApiResponse(description="Invalid administrator credentials"),
            403: OpenApiResponse(description="Access restricted to administrators")
        }
    )
    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].strip().lower()
        password = serializer.validated_data['password']

        user = User.objects.filter(email__iexact=email).first()
        if not user or not user.check_password(password):
            return Response(
                {"detail": "Invalid administrator credentials."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.is_active or user.is_deleted:
            return Response(
                {"detail": "This administrator account has been deactivated."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Enforce administrator privileges
        if not (user.is_staff or user.role in ['super_admin', 'admin']):
            return Response(
                {"detail": "Access denied. This portal is restricted to Avemaria administrators."},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "status": "success",
                "message": "Administrator login successful.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "role": user.role,
                }
            },
            status=status.HTTP_200_OK
        )


class StudentOTPRequestView(APIView):
    """
    Initiates 6-digit cryptographic OTP generation for Student password reset,
    delivering a student-branded email with 60-second validity and cooldown protection.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = OTPRequestSerializer

    @extend_schema(
        tags=['Student Authentication'],
        summary="Student OTP Password Reset Request",
        description="Sends a 6-digit verification code to the registered student email.",
        request=OTPRequestSerializer,
        responses={
            200: OTPRequestResponseSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Student account not found"),
            429: OpenApiResponse(description="Cooldown active")
        }
    )
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return Response(
                {"detail": "No registered student account found with this email address."},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.role != 'student':
            return Response(
                {"detail": "This email is registered as an administrator account. Please use the Admin Portal password reset."},
                status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.now()

        # Cooldown check
        latest_active_otp = PasswordResetOTP.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=now,
            attempts__lt=5
        ).order_by('-created_at').first()

        if latest_active_otp:
            remaining_seconds = int((latest_active_otp.expires_at - now).total_seconds())
            if remaining_seconds > 0:
                return Response(
                    {
                        "detail": f"An active verification code has already been sent. Please wait {remaining_seconds} seconds before requesting a new code.",
                        "cooldown_remaining": remaining_seconds
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

        # Invalidate prior unused OTPs
        PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)

        # Generate 6-digit cryptographic OTP
        otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
        expires_at = now + timedelta(seconds=60)

        otp_record = PasswordResetOTP.objects.create(
            user=user,
            otp=otp_code,
            expires_at=expires_at
        )

        context = {
            'user': user,
            'otp': otp_code,
            'expires_seconds': 60,
        }

        try:
            html_content = render_to_string('emails/student_otp_email.html', context)
            text_content = render_to_string('emails/student_otp_email.txt', context)

            subject = f"{otp_code} is your Avemaria verification code"
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)

            email_message = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[user.email],
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send(fail_silently=False)

        except Exception as exc:
            otp_record.delete()
            return Response(
                {"detail": f"Failed to deliver verification email: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "status": "success",
                "message": f"A 6-digit verification code has been dispatched to {user.email}.",
                "email": user.email,
                "expires_in": 60
            },
            status=status.HTTP_200_OK
        )


class StudentOTPVerifyView(APIView):
    """
    Verifies the 6-digit OTP for students. Enforces max 5 attempts and 60s expiration.
    Returns a signed reset token valid for completing the password reset.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = OTPVerifySerializer

    @extend_schema(
        tags=['Student Authentication'],
        summary="Verify Student OTP Code",
        description="Validates student 6-digit OTP and returns signed reset token.",
        request=OTPVerifySerializer,
        responses={
            200: OTPVerifyResponseSerializer,
            400: OpenApiResponse(description="Invalid or expired OTP")
        }
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].strip().lower()
        submitted_otp = serializer.validated_data['otp'].strip()

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return Response(
                {"detail": "No registered student account found with this email address."},
                status=status.HTTP_404_NOT_FOUND
            )

        otp_record = PasswordResetOTP.objects.filter(user=user).order_by('-created_at').first()
        if not otp_record:
            return Response(
                {"detail": "No verification code requested. Please request an OTP first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_record.is_used:
            return Response(
                {"detail": "This verification code has already been used. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_record.attempts >= 5:
            return Response(
                {
                    "detail": "This verification code has been disabled due to reaching the maximum 5 consecutive failed attempts. Please request a new one.",
                    "attempts_remaining": 0
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_record.is_expired():
            return Response(
                {"detail": "This verification code has expired (60s limit). Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_record.otp != submitted_otp:
            otp_record.attempts += 1
            otp_record.save(update_fields=['attempts'])
            remaining = 5 - otp_record.attempts
            if remaining <= 0:
                return Response(
                    {
                        "detail": "Invalid verification code. You have reached the maximum 5 consecutive attempts. This OTP is now disabled.",
                        "attempts_remaining": 0
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {
                    "detail": f"Invalid verification code. You have {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
                    "attempts_remaining": remaining
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        signer = TimestampSigner(salt='password-reset-otp')
        reset_token = signer.sign(f"{user.id}:{otp_record.id}")

        return Response(
            {
                "valid": True,
                "message": "Verification code verified successfully.",
                "reset_token": reset_token,
                "email": user.email
            },
            status=status.HTTP_200_OK
        )


class StudentOTPConfirmView(APIView):
    """
    Confirms student password reset using either signed reset_token or direct OTP.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = OTPPasswordResetConfirmSerializer

    @extend_schema(
        tags=['Student Authentication'],
        summary="Confirm Student Password Reset",
        description="Sets new student password using signed reset token or direct OTP.",
        request=OTPPasswordResetConfirmSerializer,
        responses={
            200: MessageResponseSerializer,
            400: OpenApiResponse(description="Invalid or expired credentials")
        }
    )
    def post(self, request):
        serializer = OTPPasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email'].strip().lower()
        new_password = serializer.validated_data['new_password']
        reset_token = serializer.validated_data.get('reset_token', '').strip()
        submitted_otp = serializer.validated_data.get('otp', '').strip()

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return Response(
                {"detail": "No registered student account found with this email address."},
                status=status.HTTP_404_NOT_FOUND
            )

        otp_record = None

        if reset_token:
            signer = TimestampSigner(salt='password-reset-otp')
            try:
                unsigned_val = signer.unsign(reset_token, max_age=600)
                user_id_str, otp_id_str = unsigned_val.split(':')
                if int(user_id_str) != user.id:
                    raise ValueError("User mismatch")
                otp_record = PasswordResetOTP.objects.get(id=int(otp_id_str), user=user)
                if otp_record.is_used:
                    return Response(
                        {"detail": "This verification session has already been used."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (SignatureExpired, BadSignature, ValueError, PasswordResetOTP.DoesNotExist):
                return Response(
                    {"detail": "Invalid or expired reset token. Please request a new code."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        elif submitted_otp:
            otp_record = PasswordResetOTP.objects.filter(user=user).order_by('-created_at').first()
            if not otp_record:
                return Response(
                    {"detail": "No verification code found. Please request an OTP first."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if otp_record.is_used:
                return Response(
                    {"detail": "This verification code has already been used. Please request a new one."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if otp_record.attempts >= 5:
                return Response(
                    {
                        "detail": "This verification code has been disabled due to reaching the maximum 5 failed attempts.",
                        "attempts_remaining": 0
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            if otp_record.is_expired():
                return Response(
                    {"detail": "This verification code has expired (60s limit). Please request a new one."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if otp_record.otp != submitted_otp:
                otp_record.attempts += 1
                otp_record.save(update_fields=['attempts'])
                remaining = 5 - otp_record.attempts
                if remaining <= 0:
                    return Response(
                        {
                            "detail": "Invalid verification code. Maximum attempts exceeded. This OTP is now disabled.",
                            "attempts_remaining": 0
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                return Response(
                    {
                        "detail": f"Invalid verification code. You have {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
                        "attempts_remaining": remaining
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        if not otp_record:
            return Response(
                {"detail": "Unable to verify credentials. Please provide a valid OTP or reset token."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])

        return Response(
            {
                "status": "success",
                "message": "Your password has been successfully reset. You can now sign in with your new password."
            },
            status=status.HTTP_200_OK
        )


class StudentCoursesView(APIView):
    """
    Returns the list of courses the authenticated student has opted to study / enrolled in.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentCoursesListResponseSerializer

    @extend_schema(
        tags=['Student Opted Courses'],
        summary="List Enrolled / Opted Courses",
        description="Returns list of courses the authenticated student is actively enrolled in.",
        responses={200: StudentCoursesListResponseSerializer}
    )
    def get(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)

        enrollments = CourseEnrollment.objects.filter(
            student=student,
            is_deleted=False
        ).select_related('course', 'course__category').order_by('-enrolled_at')

        serializer = CourseEnrollmentSerializer(enrollments, many=True, context={'request': request})
        return Response({
            "count": enrollments.count(),
            "results": serializer.data
        }, status=status.HTTP_200_OK)


class StudentCourseEnrollView(APIView):
    """
    Allows a student to opt into / enroll in a course.
    Takes 'course_id' or 'course_slug' in the request body.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentCourseEnrollSerializer

    @extend_schema(
        tags=['Student Opted Courses'],
        summary="Enroll / Opt into Course",
        description="Enrolls the student in a course by ID or slug.",
        request=StudentCourseEnrollSerializer,
        responses={
            201: StudentCourseEnrollResponseSerializer,
            200: StudentCourseEnrollResponseSerializer,
            400: OpenApiResponse(description="Either 'course_id' or 'course_slug' must be provided."),
            404: OpenApiResponse(description="Course not found or unavailable")
        }
    )
    def post(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            student, _ = Student.objects.get_or_create(
                email=request.user.email,
                defaults={'user': request.user, 'name': request.user.display_name, 'status': 'active'}
            )

        course_id = request.data.get('course_id')
        course_slug = request.data.get('course_slug')

        if not course_id and not course_slug:
            return Response(
                {"detail": "Either 'course_id' or 'course_slug' must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        course = None
        if course_id:
            course = Course.objects.filter(id=course_id, is_published=True, is_deleted=False).first()
        elif course_slug:
            course = Course.objects.filter(slug=course_slug, is_published=True, is_deleted=False).first()

        if not course:
            return Response(
                {"detail": "Course not found or is currently unavailable."},
                status=status.HTTP_404_NOT_FOUND
            )

        enrollment, created = CourseEnrollment.objects.get_or_create(
            student=student,
            course=course,
            defaults={'status': 'enrolled', 'progress_percentage': 0}
        )

        if created:
            course.enrolled_count += 1
            course.save(update_fields=['enrolled_count'])
            message = f"Successfully opted into {course.title}."
            status_code = status.HTTP_201_CREATED
        else:
            if enrollment.is_deleted:
                enrollment.is_deleted = False
                enrollment.save(update_fields=['is_deleted'])
            message = f"You are already opted into {course.title}."
            status_code = status.HTTP_200_OK

        serializer = CourseEnrollmentSerializer(enrollment, context={'request': request})
        return Response({
            "status": "success",
            "message": message,
            "enrollment": serializer.data
        }, status=status_code)


class StudentCourseDropView(APIView):
    """
    Allows a student to unenroll or remove an opted course.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Student Opted Courses'],
        summary="Drop / Unenroll Course",
        description="Removes a course enrollment for the authenticated student.",
        responses={
            200: MessageResponseSerializer,
            404: OpenApiResponse(description="Enrollment not found")
        }
    )
    def delete(self, request, course_id):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        enrollment = CourseEnrollment.objects.filter(student=student, course_id=course_id).first()
        if not enrollment:
            return Response({"detail": "You are not enrolled in this course."}, status=status.HTTP_404_NOT_FOUND)

        enrollment.delete()
        if enrollment.course.enrolled_count > 0:
            enrollment.course.enrolled_count -= 1
            enrollment.course.save(update_fields=['enrolled_count'])

        return Response({
            "status": "success",
            "message": f"Successfully dropped {enrollment.course.title}."
        }, status=status.HTTP_200_OK)


class StudentPurchasedResourcesView(APIView):
    """
    Returns the list of study resources purchased by the authenticated student.
    Matches the student interface card with Category badge, Title, Description,
    Formatted Purchase Date ("Purchased 31 Aug 2026"), and Access resource button.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentPurchasedResourcesListResponseSerializer

    @extend_schema(
        tags=['Student Resource Purchases'],
        summary="List Purchased Resources",
        description="Returns list of study resources unlocked / purchased by the student.",
        responses={200: StudentPurchasedResourcesListResponseSerializer}
    )
    def get(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)

        category = request.query_params.get('category')
        search = request.query_params.get('search')

        purchases = ResourcePurchase.objects.filter(
            student=student,
            is_deleted=False
        ).select_related('resource').prefetch_related('resource__pdf_files')

        if category:
            purchases = purchases.filter(resource__category__iexact=category)
        if search:
            purchases = purchases.filter(
                Q(resource__title__icontains=search) | Q(resource__description__icontains=search)
            )

        purchases = purchases.order_by('-purchased_at')
        serializer = ResourcePurchaseSerializer(purchases, many=True, context={'request': request})
        return Response({
            "count": purchases.count(),
            "results": serializer.data
        }, status=status.HTTP_200_OK)


class StudentResourcePurchaseView(APIView):
    """
    Allows a student to purchase / unlock a paid study resource.
    Takes 'resource_id' or 'resource_slug' in the request body.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentResourcePurchaseSerializer

    @extend_schema(
        tags=['Student Resource Purchases'],
        summary="Purchase Study Resource",
        description="Unlocks a paid study resource for the authenticated student and sends an invoice receipt email.",
        request=StudentResourcePurchaseSerializer,
        responses={
            201: StudentResourcePurchaseResponseSerializer,
            200: StudentResourcePurchaseResponseSerializer,
            400: OpenApiResponse(description="Missing resource identifier or validation error"),
            404: OpenApiResponse(description="Resource not found")
        }
    )
    def post(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            student, _ = Student.objects.get_or_create(
                email=request.user.email,
                defaults={'user': request.user, 'name': request.user.display_name, 'status': 'active'}
            )

        resource_id = request.data.get('resource_id')
        resource_slug = request.data.get('resource_slug')

        if not resource_id and not resource_slug:
            return Response(
                {"detail": "Either 'resource_id' or 'resource_slug' must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        resource = None
        if resource_id:
            resource = PaidResource.objects.filter(id=resource_id, is_active=True, is_deleted=False).first()
        elif resource_slug:
            resource = PaidResource.objects.filter(slug=resource_slug, is_active=True, is_deleted=False).first()

        if not resource:
            return Response(
                {"detail": "Resource not found or is currently unavailable."},
                status=status.HTTP_404_NOT_FOUND
            )

        order_id = request.data.get('order_id', '')
        amount_paid = request.data.get('amount_paid', resource.price)
        payment_status = request.data.get('payment_status', 'paid')
        payment_method = request.data.get('payment_method', 'demo')

        purchase, created = ResourcePurchase.objects.get_or_create(
            student=student,
            resource=resource,
            defaults={
                'amount_paid': amount_paid,
                'currency': resource.currency,
                'order_id': order_id,
                'status': 'active',
                'payment_status': payment_status,
                'payment_method': payment_method
            }
        )

        if not created:
            if purchase.status != 'active':
                purchase.status = 'active'
                purchase.is_deleted = False
            if 'payment_status' in request.data:
                purchase.payment_status = payment_status
            if 'payment_method' in request.data:
                purchase.payment_method = payment_method
            purchase.save()

        # Send invoice / payment receipt email if payment is completed
        if purchase.payment_status == 'paid':
            send_purchase_receipt_email(purchase, request=request)

        serializer = ResourcePurchaseSerializer(purchase, context={'request': request})
        return Response({
            "status": "success",
            "message": f"Successfully purchased {resource.title}.",
            "receipt_emailed": purchase.receipt_emailed,
            "purchase": serializer.data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)



class StudentResourceAccessView(APIView):
    """
    Logs an access or download action for a purchased resource and returns access/file URLs.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentResourceAccessResponseSerializer

    @extend_schema(
        tags=['Student Resource Purchases'],
        summary="Access Purchased Resource Files (POST)",
        description="Logs an access event and returns resource details and PDF file download URLs.",
        responses={
            200: StudentResourceAccessResponseSerializer,
            403: OpenApiResponse(description="Resource not purchased or access expired"),
            404: OpenApiResponse(description="Student profile not found")
        }
    )
    def post(self, request, resource_id):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        purchase = ResourcePurchase.objects.filter(
            student=student,
            resource_id=resource_id,
            is_deleted=False,
            status='active'
        ).select_related('resource').prefetch_related('resource__pdf_files').first()

        if not purchase:
            return Response(
                {"detail": "You have not purchased this resource or your access has expired."},
                status=status.HTTP_403_FORBIDDEN
            )

        purchase.download_count += 1
        purchase.last_accessed_at = timezone.now()
        purchase.save(update_fields=['download_count', 'last_accessed_at'])

        serializer = ResourcePurchaseSerializer(purchase, context={'request': request})
        return Response({
            "status": "success",
            "message": "Resource access verified.",
            "purchase": serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Student Resource Purchases'],
        summary="Access Purchased Resource Files (GET)",
        description="Returns resource details and PDF file download URLs.",
        responses={
            200: StudentResourceAccessResponseSerializer,
            403: OpenApiResponse(description="Resource not purchased or access expired"),
            404: OpenApiResponse(description="Student profile not found")
        }
    )
    def get(self, request, resource_id):
        return self.post(request, resource_id)


class StudentPurchaseHistoryView(APIView):
    """
    Returns the purchase history table data for the authenticated student.
    Matches the columns: SL. NO | RESOURCE | DATE | AMOUNT | STATUS
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentPurchaseHistoryListResponseSerializer

    @extend_schema(
        tags=['Student Invoices & Payments'],
        summary="Student Purchase History Register",
        description="Returns structured purchase history matching the student portal table.",
        responses={200: StudentPurchaseHistoryListResponseSerializer}
    )
    def get(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)

        status_param = request.query_params.get('status')
        search = request.query_params.get('search')

        purchases = ResourcePurchase.objects.filter(
            student=student,
            is_deleted=False
        ).select_related('resource').prefetch_related('resource__pdf_files')

        if status_param:
            purchases = purchases.filter(payment_status__iexact=status_param)
        if search:
            purchases = purchases.filter(
                Q(resource__title__icontains=search) | Q(order_id__icontains=search)
            )

        purchases = list(purchases.order_by('-purchased_at'))

        # Assign 1-indexed SL. NO
        for idx, item in enumerate(purchases, start=1):
            item.sl_no = idx

        serializer = StudentPurchaseHistorySerializer(purchases, many=True, context={'request': request})
        return Response({
            "count": len(purchases),
            "results": serializer.data
        }, status=status.HTTP_200_OK)


class StudentPaymentDetailsView(APIView):
    """
    Returns payment summary cards (Total Spent, Completed Payments),
    payment methods notice, and individual transaction rows matching the
    student payment details interface.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentPaymentDetailsResponseSerializer

    @extend_schema(
        tags=['Student Invoices & Payments'],
        summary="Student Payment Details & Spending Summary",
        description="Returns total spent KPI, payment methods notice, and individual transaction rows.",
        responses={200: StudentPaymentDetailsResponseSerializer}
    )
    def get(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({
                "summary": {
                    "total_spent": "0.00",
                    "total_spent_formatted": "£0.00",
                    "currency": "£",
                    "completed_payments": 0,
                    "pending_payments": 0,
                    "total_transactions": 0
                },
                "payment_methods_notice": {
                    "title": "Payment methods",
                    "note": "Card details are never stored on our servers. Every payment is taken on our payment provider’s secure checkout, and your saved cards are managed there."
                },
                "results": []
            }, status=status.HTTP_200_OK)

        purchases = ResourcePurchase.objects.filter(
            student=student,
            is_deleted=False
        ).select_related('resource').order_by('-purchased_at')

        paid_purchases = purchases.filter(payment_status='paid')
        completed_count = paid_purchases.count()
        pending_count = purchases.filter(payment_status='pending').count()

        total_val = paid_purchases.aggregate(total=Sum('amount_paid'))['total'] or 0.00
        currency = '£'
        first_p = purchases.first()
        if first_p and first_p.currency:
            currency = first_p.currency

        serializer = StudentPaymentDetailItemSerializer(purchases, many=True, context={'request': request})

        return Response({
            "summary": {
                "total_spent": f"{total_val:.2f}",
                "total_spent_formatted": f"{currency}{total_val:.2f}",
                "currency": currency,
                "completed_payments": completed_count,
                "pending_payments": pending_count,
                "total_transactions": purchases.count()
            },
            "payment_methods_notice": {
                "title": "Payment methods",
                "note": "Card details are never stored on our servers. Every payment is taken on our payment provider’s secure checkout, and your saved cards are managed there."
            },
            "results": serializer.data
        }, status=status.HTTP_200_OK)


class StudentReceiptsView(APIView):
    """
    Returns the list of purchase receipts / invoices for the authenticated student.
    Matches the receipt item interface:
    - Title: Resource Title
    - Subtitle: Date · £Amount
    - Status: "Receipt emailed to you"
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentReceiptsListResponseSerializer

    @extend_schema(
        tags=['Student Invoices & Payments'],
        summary="List Student Invoices / Receipts",
        description="Returns invoice and receipt cards for all completed purchases.",
        responses={200: StudentReceiptsListResponseSerializer}
    )
    def get(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)

        purchases = ResourcePurchase.objects.filter(
            student=student,
            is_deleted=False
        ).select_related('resource').prefetch_related('resource__pdf_files').order_by('-purchased_at')

        serializer = StudentReceiptSerializer(purchases, many=True, context={'request': request})
        return Response({
            "count": purchases.count(),
            "results": serializer.data
        }, status=status.HTTP_200_OK)


class StudentReceiptResendView(APIView):
    """
    Re-dispatches the payment receipt / invoice email to the student's email address.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentReceiptResendResponseSerializer

    @extend_schema(
        tags=['Student Invoices & Payments'],
        summary="Resend Purchase Receipt Email",
        description="Re-dispatches the official branded purchase receipt / tax invoice to the student's email.",
        responses={
            200: StudentReceiptResendResponseSerializer,
            404: OpenApiResponse(description="Receipt not found"),
            500: OpenApiResponse(description="Email dispatch failed")
        }
    )
    def post(self, request, purchase_id):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        purchase = ResourcePurchase.objects.filter(
            student=student,
            id=purchase_id,
            is_deleted=False
        ).select_related('resource').first()

        if not purchase:
            return Response({"detail": "Receipt not found."}, status=status.HTTP_404_NOT_FOUND)

        sent = send_purchase_receipt_email(purchase, request=request)
        if sent:
            return Response({
                "status": "success",
                "message": f"Receipt for {purchase.resource.title} has been emailed to {student.email}.",
                "receipt_emailed": True,
                "receipt_emailed_at": purchase.receipt_emailed_at
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "warning",
                "message": "Unable to dispatch receipt email at this time. Please try again shortly."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StudentChangePasswordView(APIView):
    """
    Allows an authenticated student to update their password from the portal interface.
    Inputs match the form:
    - current_password
    - new_password
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentChangePasswordSerializer

    @extend_schema(
        tags=['Student Authentication'],
        summary="Change Student Password",
        description="Updates password from the student portal interface.",
        request=StudentChangePasswordSerializer,
        responses={
            200: MessageResponseSerializer,
            400: OpenApiResponse(description="Validation error")
        }
    )
    def post(self, request):
        serializer = StudentChangePasswordSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        new_password = serializer.validated_data['new_password']
        user.set_password(new_password)
        user.save()

        return Response({
            "status": "success",
            "message": "Password updated successfully."
        }, status=status.HTTP_200_OK)


class StudentLogoutView(APIView):
    """
    Signs the student out of their account on this device.
    Optionally invalidates the provided refresh token.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentLogoutSerializer

    @extend_schema(
        tags=['Student Authentication'],
        summary="Student Sign Out / Logout",
        description="Signs the student out and optionally blacklists the provided refresh token.",
        request=StudentLogoutSerializer,
        responses={200: MessageResponseSerializer}
    )
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        return Response({
            "status": "success",
            "message": "Signed out successfully."
        }, status=status.HTTP_200_OK)






