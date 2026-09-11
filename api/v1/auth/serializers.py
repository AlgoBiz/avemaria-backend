from rest_framework import serializers
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

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class StudentProfileSerializer(serializers.ModelSerializer):
    institution_and_year = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    documents = StudentDocumentSerializer(many=True, read_only=True)

    # Aliases matching frontend field naming
    full_name = serializers.CharField(source='name', required=False)
    highest_qualification = serializers.CharField(source='qualification', required=False)
    university = serializers.CharField(source='institution', required=False)
    year_of_graduation = serializers.CharField(source='graduating_year', required=False)

    class Meta:
        from apps.students.models import Student
        model = Student
        fields = (
            'id', 'avatar',
            # Personal Details
            'name', 'full_name', 'email', 'phone', 'whatsapp', 'date_of_birth', 'gender', 'nationality',
            # Address Details
            'address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country',
            # Academic & Professional Details
            'qualification', 'highest_qualification', 'institution', 'university',
            'graduating_year', 'year_of_graduation', 'institution_and_year',
            'current_role', 'employer_hospital', 'years_of_experience',
            # Passport Details
            'passport_number', 'country_of_issue', 'passport_expiry_date',
            # Documents
            'documents',
            # General / System
            'location', 'status', 'status_display',
            'registered_date', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'email', 'status', 'status_display',
            'institution_and_year', 'documents', 'registered_date', 'created_at', 'updated_at'
        )


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

