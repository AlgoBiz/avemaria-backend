from datetime import datetime, date
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.accounts.models import User


class AdminProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'display_name', 'role', 'avatar', 'is_active', 'is_deleted', 'created_at', 'updated_at')

class AdminProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('display_name', 'email', 'avatar')

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=False, write_only=True)
    new_password = serializers.CharField(required=True, min_length=6, write_only=True)
    confirm_new_password = serializers.CharField(required=False, allow_blank=True, min_length=6, write_only=True)

    def validate(self, data):
        if data.get('confirm_new_password') and data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})
        return data


class StudentChangePasswordSerializer(serializers.Serializer):
    """
    Serializer matching the Student Portal 'Change Password' form:
    Fields: current_password, new_password
    """
    current_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Current account password"
    )
    new_password = serializers.CharField(
        required=True,
        min_length=6,
        write_only=True,
        style={'input_type': 'password'},
        help_text="New password (minimum 6 characters)"
    )

    def validate_current_password(self, value):
        request = self.context.get('request')
        if request and request.user:
            if not request.user.check_password(value):
                raise serializers.ValidationError("The current password you entered is incorrect.")
        return value

    def validate(self, data):
        if data.get('current_password') and data.get('new_password'):
            if data['current_password'] == data['new_password']:
                raise serializers.ValidationError({"new_password": "New password cannot be the same as your current password."})
        return data



class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    frontend_url = serializers.CharField(required=False, allow_blank=True, default='')


class PasswordResetValidateTokenSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6, write_only=True)
    confirm_new_password = serializers.CharField(required=True, min_length=6, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})
        return data


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)


class OTPPasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=False, allow_blank=True, min_length=6, max_length=6)
    reset_token = serializers.CharField(required=False, allow_blank=True)
    new_password = serializers.CharField(required=True, min_length=6, write_only=True)
    confirm_new_password = serializers.CharField(required=True, min_length=6, write_only=True)

    def validate(self, data):
        if not data.get('otp') and not data.get('reset_token'):
            raise serializers.ValidationError("Either 'otp' or 'reset_token' must be provided.")
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})
        return data


class StudentRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, min_length=6, write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True, default='', max_length=50)
    qualification = serializers.CharField(required=False, allow_blank=True, default='', max_length=150)
    institution = serializers.CharField(required=False, allow_blank=True, default='', max_length=200)
    graduating_year = serializers.CharField(required=False, allow_blank=True, default='', max_length=50)
    location = serializers.CharField(required=False, allow_blank=True, default='', max_length=150)

    def validate(self, data):
        name_val = data.get('full_name') or data.get('name')
        if not name_val or not name_val.strip():
            raise serializers.ValidationError({"full_name": "Full name is required."})
        data['resolved_name'] = name_val.strip()

        email = data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "An account with this email address already exists."})
        data['email'] = email
        return data


class StudentLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class StudentDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        from apps.students.models import StudentDocument
        model = StudentDocument
        fields = (
            'id', 'document_type', 'document_type_display', 'title',
            'file', 'file_url', 'file_name', 'file_size', 'uploaded_at'
        )
        read_only_fields = ('id', 'file_url', 'file_name', 'file_size', 'uploaded_at')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class FlexibleDateField(serializers.DateField):
    """
    Resilient date field accepting ISO-8601 (YYYY-MM-DD), DD/MM/YYYY, MM/DD/YYYY,
    DD-MM-YYYY, ISO datetime strings, and converting empty strings/nulls to None.
    """
    def to_internal_value(self, value):
        if value in (None, '', 'null', 'None'):
            return None
        if isinstance(value, (datetime, date)):
            return value if isinstance(value, date) else value.date()
        if isinstance(value, str):
            clean_str = value.split('T')[0].strip()
            if not clean_str or clean_str in ('null', 'None'):
                return None
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y', '%Y/%m/%d'):
                try:
                    return datetime.strptime(clean_str, fmt).date()
                except ValueError:
                    continue
        return super().to_internal_value(value)


class StudentProfileSerializer(serializers.ModelSerializer):
    documents = StudentDocumentSerializer(many=True, read_only=True)
    date_of_birth = FlexibleDateField(required=False, allow_null=True)
    passport_expiry_date = FlexibleDateField(required=False, allow_null=True)
    full_name = serializers.CharField(source='name', required=False, allow_blank=True)
    highest_qualification = serializers.CharField(source='qualification', required=False, allow_blank=True)
    dob = FlexibleDateField(source='date_of_birth', required=False, allow_null=True)

    class Meta:
        from apps.students.models import Student
        model = Student
        fields = (
            'id',
            'full_name',
            'email',
            'phone',
            'whatsapp',
            'date_of_birth',
            'dob',
            'gender',
            'nationality',
            'address_line_1',
            'address_line_2',
            'city',
            'state',
            'postal_code',
            'country',
            'highest_qualification',
            'institution',
            'graduating_year',
            'current_role',
            'employer_hospital',
            'years_of_experience',
            'passport_number',
            'country_of_issue',
            'passport_expiry_date',
            'documents',
            'status',
            'registered_date',
            'created_at',
            'updated_at'
        )
        read_only_fields = (
            'id', 'email', 'status', 'documents', 'registered_date', 'created_at', 'updated_at'
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        elif isinstance(data, dict):
            data = dict(data)

        # Mapping variations from different frontends/forms to the target model fields
        alias_map = {
            'full_name': 'name',
            'highest_qualification': 'qualification',
            'university': 'institution',
            'university_institution': 'institution',
            'year_of_graduation': 'graduating_year',
            'expiry_date': 'passport_expiry_date',
            'passport_expiry': 'passport_expiry_date',
            'dob': 'date_of_birth',
            'address_line1': 'address_line_1',
            'address1': 'address_line_1',
            'address_line2': 'address_line_2',
            'address2': 'address_line_2',
            'city_town': 'city',
            'state_region': 'state',
            'region': 'state',
            'employer': 'employer_hospital',
            'hospital': 'employer_hospital',
            'experience': 'years_of_experience',
            'whatsapp_number': 'whatsapp',
            'postalCode': 'postal_code',
            'postcode': 'postal_code',
            'zip_code': 'postal_code',
        }
        for alias_key, target_key in alias_map.items():
            if alias_key in data and (target_key not in data or data[target_key] in ('', None)):
                data[target_key] = data[alias_key]

        return super().to_internal_value(data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['full_name'] = instance.name
        ret['highest_qualification'] = instance.qualification
        ret['dob'] = str(instance.date_of_birth) if instance.date_of_birth else None
        return ret


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class AdminLoginResponseUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    display_name = serializers.CharField()
    role = serializers.CharField()


class AdminLoginResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = AdminLoginResponseUserSerializer()


class MessageResponseSerializer(serializers.Serializer):
    status = serializers.CharField(required=False, default="success")
    message = serializers.CharField()


class PasswordResetRequestResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    email = serializers.EmailField()
    valid_hours = serializers.IntegerField()


class PasswordResetValidateResponseSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    email = serializers.EmailField(required=False)
    display_name = serializers.CharField(required=False)
    detail = serializers.CharField(required=False)


class OTPRequestResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    email = serializers.EmailField()
    expires_in = serializers.IntegerField()


class OTPVerifyResponseSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    message = serializers.CharField()
    reset_token = serializers.CharField()
    email = serializers.EmailField()


class StudentLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True, help_text="JWT refresh token to blacklist")


class StudentDocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True, help_text="Document or image file to upload")
    document_type = serializers.CharField(required=False, default="other", help_text="Document category (e.g. passport, aadhar, bank_passbook, degree_certificate, cv, other)")
    title = serializers.CharField(required=False, allow_blank=True, help_text="Title or label for the document")


class StudentDocumentUploadResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    document = StudentDocumentSerializer()


class StudentCourseEnrollSerializer(serializers.Serializer):
    course_id = serializers.IntegerField(required=False, allow_null=True, help_text="ID of the course")
    course_slug = serializers.CharField(required=False, allow_blank=True, help_text="Slug of the course")


class StudentCourseEnrollResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    enrollment = serializers.DictField()


class StudentCoursesListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


class StudentResourcePurchaseSerializer(serializers.Serializer):
    resource_id = serializers.IntegerField(required=False, allow_null=True, help_text="ID of the paid resource")
    resource_slug = serializers.CharField(required=False, allow_blank=True, help_text="Slug of the paid resource")
    order_id = serializers.CharField(required=False, allow_blank=True, help_text="External checkout or transaction ID")
    amount_paid = serializers.DecimalField(required=False, max_digits=10, decimal_places=2, help_text="Amount paid")
    payment_status = serializers.CharField(required=False, default="paid", help_text="Payment status: paid, pending, failed")
    payment_method = serializers.CharField(required=False, default="demo", help_text="Payment method used")


class StudentResourcePurchaseResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    receipt_emailed = serializers.BooleanField()
    purchase = serializers.DictField()


class StudentResourceAccessResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    purchase = serializers.DictField()


class StudentPurchasedResourcesListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


class StudentPurchaseHistoryListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


class StudentPaymentDetailsSummarySerializer(serializers.Serializer):
    total_spent = serializers.CharField()
    total_spent_formatted = serializers.CharField()
    currency = serializers.CharField()
    completed_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    total_transactions = serializers.IntegerField()


class StudentPaymentDetailsNoticeSerializer(serializers.Serializer):
    title = serializers.CharField()
    note = serializers.CharField()


class StudentPaymentDetailsResponseSerializer(serializers.Serializer):
    summary = StudentPaymentDetailsSummarySerializer()
    payment_methods_notice = StudentPaymentDetailsNoticeSerializer()
    results = serializers.ListField(child=serializers.DictField())


class StudentReceiptsListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


class StudentReceiptResendResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    receipt_emailed = serializers.BooleanField()
    receipt_emailed_at = serializers.DateTimeField(allow_null=True)


