from rest_framework import serializers
from apps.enquiries.models import Enquiry

class EnquiryCreateSerializer(serializers.ModelSerializer):
    programme_interest = serializers.CharField(write_only=True, required=False, allow_blank=True)
    subject = serializers.CharField(write_only=True, required=False, allow_blank=True)
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Enquiry
        fields = (
            'id', 'candidate_name', 'name', 'full_name', 'email', 'phone',
            'topic', 'programme_interest', 'subject', 'message',
            'status', 'status_display', 'created_at'
        )
        extra_kwargs = {
            'candidate_name': {'required': False},
            'topic': {'required': False},
            'phone': {'required': False, 'allow_blank': True, 'allow_null': True},
            'message': {'required': True}
        }

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = data.copy()

        # Name alias (matching "Full name" field in student form)
        if not data.get('candidate_name'):
            for alias in ['full_name', 'name', 'fullName', 'student_name']:
                if data.get(alias):
                    data['candidate_name'] = data[alias]
                    break

        # Topic / Selected Pill alias (matching top pill options like "Licensing preparation", etc.)
        if not data.get('topic') and not data.get('programme_interest'):
            for alias in ['interest', 'programme', 'category', 'goal', 'course', 'discipline', 'pill']:
                if data.get(alias):
                    data['topic'] = data[alias]
                    break

        # Subject alias
        if not data.get('subject'):
            for alias in ['inquiry_subject', 'title', 'heading']:
                if data.get(alias):
                    data['subject'] = data[alias]
                    break

        # Phone alias
        if not data.get('phone'):
            for alias in ['phone_number', 'mobile', 'tel', 'contact']:
                if data.get(alias):
                    data['phone'] = data[alias]
                    break

        # Message alias
        if not data.get('message'):
            for alias in ['query', 'content', 'body', 'comments', 'enquiry']:
                if data.get(alias):
                    data['message'] = data[alias]
                    break

        return super().to_internal_value(data)

    def validate(self, attrs):
        if not attrs.get('candidate_name'):
            raise serializers.ValidationError({'candidate_name': 'Full name is required.'})
        return attrs

    def create(self, validated_data):
        programme_interest = validated_data.pop('programme_interest', None)
        subject = validated_data.pop('subject', None)
        validated_data.pop('full_name', None)
        validated_data.pop('name', None)

        if not validated_data.get('topic') and programme_interest:
            validated_data['topic'] = programme_interest
        elif not validated_data.get('topic'):
            validated_data['topic'] = 'Licensing preparation'

        if subject:
            original_msg = validated_data.get('message', '')
            if not original_msg.startswith(f"{subject}:"):
                validated_data['message'] = f"{subject}: {original_msg}"

        # Status always defaults strictly to 'new' (New Lead) upon creation from student/user side
        validated_data['status'] = 'new'
        return super().create(validated_data)


class EnquiryAdminSerializer(serializers.ModelSerializer):
    message_snippet = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    received_at = serializers.DateTimeField(source='created_at', read_only=True)
    programme_interest = serializers.CharField(source='topic', read_only=True)
    inquiry_subject = serializers.CharField(read_only=True)
    original_message = serializers.CharField(source='original_message_body', read_only=True)
    received_date_formatted = serializers.SerializerMethodField()
    logged_date_display = serializers.SerializerMethodField()

    class Meta:
        model = Enquiry
        fields = (
            'id', 'candidate_name', 'email', 'phone', 'topic', 'programme_interest',
            'inquiry_subject', 'message', 'original_message', 'message_snippet',
            'status', 'status_display', 'is_active', 'is_deleted',
            'received_at', 'received_date_formatted', 'logged_date_display', 'updated_at'
        )
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'status': {'required': False}
        }

    def validate_status(self, value):
        valid_statuses = [choice[0] for choice in Enquiry.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status '{value}'. Allowed: {valid_statuses}")
        return value

    def get_received_date_formatted(self, obj):
        if obj.created_at:
            day = obj.created_at.strftime('%d').lstrip('0')
            month = obj.created_at.strftime('%b')
            # If September, display 'Sept' to match UI screenshot '10 Sept 2026'
            if month == 'Sep':
                month = 'Sept'
            return f"{day} {month} {obj.created_at.strftime('%Y')}"
        return ""

    def get_logged_date_display(self, obj):
        date_str = self.get_received_date_formatted(obj)
        return f"Logged {date_str}" if date_str else ""
