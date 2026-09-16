from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import (
    CustomTokenObtainPairView,
    AdminProfileView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetValidateTokenView,
    PasswordResetConfirmView,
    OTPRequestView,
    OTPVerifyView,
    OTPPasswordResetConfirmView,
    StudentRegisterView,
    StudentLoginView,
    StudentProfileView,
    AdminLoginView,
    StudentOTPRequestView,
    StudentOTPVerifyView,
    StudentOTPConfirmView,
    StudentDocumentUploadView,
    StudentDocumentDeleteView,
    StudentCoursesView,
    StudentCourseEnrollView,
    StudentCourseDropView,
    StudentPurchasedResourcesView,
    StudentPurchasedResourceDetailView,
    StudentResourcePurchaseView,
    StudentResourceAccessView,
    StudentPurchaseHistoryView,
    StudentPurchaseHistoryDetailView,
    StudentPaymentDetailsView,
    StudentReceiptsView,
    StudentReceiptDetailView,
    StudentReceiptResendView,
    StudentChangePasswordView,
    StudentLogoutView,
)

urlpatterns = [
    # General / SimpleJWT Backward Compatibility
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Dedicated Administrator Authentication
    path('admin/login/', AdminLoginView.as_view(), name='admin_login'),
    path('profile/', AdminProfileView.as_view(), name='admin_profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/validate-token/', PasswordResetValidateTokenView.as_view(), name='password_reset_validate_token'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Admin Email OTP Password Reset Endpoints
    path('otp/request/', OTPRequestView.as_view(), name='otp_request'),
    path('otp/verify/', OTPVerifyView.as_view(), name='otp_verify'),
    path('otp/confirm/', OTPPasswordResetConfirmView.as_view(), name='otp_confirm'),

    # Dedicated Student Authentication & Profile Endpoints
    path('student/register/', StudentRegisterView.as_view(), name='student_register'),
    path('student/login/', StudentLoginView.as_view(), name='student_login'),
    path('student/profile/', StudentProfileView.as_view(), name='student_profile'),
    path('student/change-password/', StudentChangePasswordView.as_view(), name='student_change_password'),
    path('student/update-password/', StudentChangePasswordView.as_view(), name='student_update_password'),
    path('student/logout/', StudentLogoutView.as_view(), name='student_logout'),

    # Student Dedicated OTP Password Reset Endpoints
    path('student/forgot-password/', StudentOTPRequestView.as_view(), name='student_forgot_password'),
    path('student/otp/request/', StudentOTPRequestView.as_view(), name='student_otp_request'),
    path('student/otp/verify/', StudentOTPVerifyView.as_view(), name='student_otp_verify'),
    path('student/otp/confirm/', StudentOTPConfirmView.as_view(), name='student_otp_confirm'),

    # Student Document Upload & Management Endpoints
    path('student/documents/', StudentDocumentUploadView.as_view(), name='student_document_upload'),
    path('student/documents/<int:pk>/', StudentDocumentDeleteView.as_view(), name='student_document_delete'),

    # Student Opted Courses Endpoints
    path('student/courses/', StudentCoursesView.as_view(), name='student_courses'),
    path('student/courses/enroll/', StudentCourseEnrollView.as_view(), name='student_course_enroll'),
    path('student/courses/<int:course_id>/', StudentCourseDropView.as_view(), name='student_course_drop'),

    # Student Purchased Resources Endpoints
    path('student/resources/', StudentPurchasedResourcesView.as_view(), name='student_resources'),
    path('student/resources/<int:pk>/', StudentPurchasedResourceDetailView.as_view(), name='student_resource_detail'),
    path('student/resources/purchase/', StudentResourcePurchaseView.as_view(), name='student_resource_purchase'),
    path('student/resources/<int:resource_id>/access/', StudentResourceAccessView.as_view(), name='student_resource_access'),

    # Student Purchase History Endpoints
    path('student/purchase-history/', StudentPurchaseHistoryView.as_view(), name='student_purchase_history'),
    path('student/purchase-history/<int:purchase_id>/', StudentPurchaseHistoryDetailView.as_view(), name='student_purchase_history_detail'),
    path('student/purchases/', StudentPurchaseHistoryView.as_view(), name='student_purchases'),
    path('student/purchases/<int:purchase_id>/', StudentPurchaseHistoryDetailView.as_view(), name='student_purchases_detail'),

    # Student Payment Details Endpoints
    path('student/payments/', StudentPaymentDetailsView.as_view(), name='student_payments'),
    path('student/payment-details/', StudentPaymentDetailsView.as_view(), name='student_payment_details'),

    # Student Invoices / Receipts Endpoints
    path('student/receipts/', StudentReceiptsView.as_view(), name='student_receipts'),
    path('student/receipts/<int:purchase_id>/', StudentReceiptDetailView.as_view(), name='student_receipt_detail'),
    path('student/invoices/', StudentReceiptsView.as_view(), name='student_invoices'),
    path('student/invoices/<int:purchase_id>/', StudentReceiptDetailView.as_view(), name='student_invoice_detail'),
    path('student/receipts/<int:purchase_id>/resend/', StudentReceiptResendView.as_view(), name='student_receipt_resend'),
]





