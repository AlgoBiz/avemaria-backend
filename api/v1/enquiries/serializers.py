from rest_framework import serializers
from apps.enquiries.models import Enquiry

class EnquiryCreateSerializer(serializers.ModelSerializer):
    programme_interest = serializers.CharField(write_only=True, required=False)
    subject = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Enquiry
        fields = ('id', 'candidate_name', 'email', 'phone', 'topic', 'programme_interest', 'subject', 'message')
        extra_kwargs = {
            'topic': {'required': False},
            'phone': {'required': False, 'allow_blank': True}
        }

    def create(self, validated_data):
        programme_interest = validated_data.pop('programme_interest', None)
        subject = validated_data.pop('subject', None)
        
        if not validated_data.get('topic') and programme_interest:
            validated_data['topic'] = programme_interest
        elif not validated_data.get('topic'):
            validated_data['topic'] = 'General Enquiry'

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
