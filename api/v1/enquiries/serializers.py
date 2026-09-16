from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.enquiries.models import Enquiry

class EnquiryCreateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(required=False)
    course_name = serializers.CharField(required=False)
    subject = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)

    # Backward-compatible input fields
    candidate_name = serializers.CharField(required=False, write_only=True)
    name = serializers.CharField(required=False, write_only=True)
    topic = serializers.CharField(required=False, write_only=True)
    programme_interest = serializers.CharField(required=False, allow_blank=True, write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Enquiry
        fields = (
            'id', 'full_name', 'email', 'phone',
            'course_name', 'subject', 'message',
            'candidate_name', 'name', 'topic', 'programme_interest',
            'status', 'status_display', 'created_at'
        )
        extra_kwargs = {
            'candidate_name': {'write_only': True, 'required': False},
            'name': {'write_only': True, 'required': False},
            'topic': {'write_only': True, 'required': False},
            'programme_interest': {'write_only': True, 'required': False},
            'phone': {'required': False, 'allow_blank': True, 'allow_null': True},
            'status': {'read_only': True},
        }

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data = data.dict()
        elif hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)

        # Full name aliases ("full_name", "ful name", "fullname", "candidate_name", "name")
        if not data.get('candidate_name') and not data.get('full_name'):
            for alias in ['full_name', 'ful name', 'ful_name', 'fullname', 'name', 'fullName', 'student_name', 'candidate_name']:
                if data.get(alias):
                    data['candidate_name'] = data[alias]
                    data['full_name'] = data[alias]
                    break
        elif data.get('full_name') and not data.get('candidate_name'):
            data['candidate_name'] = data['full_name']
        elif data.get('candidate_name') and not data.get('full_name'):
            data['full_name'] = data['candidate_name']

        # Course name aliases ("course_name", "course name", "course", "topic", "programme_interest")
        if not data.get('topic') and not data.get('course_name'):
            for alias in ['course_name', 'course name', 'course', 'topic', 'programme_interest', 'interest', 'programme', 'category']:
                if data.get(alias):
                    data['topic'] = data[alias]
                    data['course_name'] = data[alias]
                    break
        elif data.get('course_name') and not data.get('topic'):
            data['topic'] = data['course_name']
        elif data.get('topic') and not data.get('course_name'):
            data['course_name'] = data['topic']

        # Subject aliases
        if not data.get('subject'):
            for alias in ['inquiry_subject', 'title', 'heading']:
                if data.get(alias):
                    data['subject'] = data[alias]
                    break

        # Phone aliases
        if not data.get('phone'):
            for alias in ['phone_number', 'mobile', 'tel', 'contact']:
                if data.get(alias):
                    data['phone'] = data[alias]
                    break

        # Message aliases
        if not data.get('message'):
            for alias in ['query', 'content', 'body', 'comments', 'enquiry']:
                if data.get(alias):
                    data['message'] = data[alias]
                    break

        return super().to_internal_value(data)

    def validate(self, attrs):
        if not attrs.get('candidate_name') and not attrs.get('full_name'):
            raise serializers.ValidationError({'full_name': 'Full name is required.'})
        return attrs

    def create(self, validated_data):
        programme_interest = validated_data.pop('programme_interest', None)
        subject = validated_data.pop('subject', None)
        validated_data.pop('name', None)
        full_name = validated_data.pop('full_name', None)
        course_name = validated_data.pop('course_name', None)

        if not validated_data.get('candidate_name') and full_name:
            validated_data['candidate_name'] = full_name

        if not validated_data.get('topic'):
            if course_name:
                validated_data['topic'] = course_name
            elif programme_interest:
                validated_data['topic'] = programme_interest
            else:
                validated_data['topic'] = 'Licensing preparation'

        if subject:
            original_msg = validated_data.get('message', '')
            if not original_msg.startswith(f"{subject}:"):
                validated_data['message'] = f"{subject}: {original_msg}"

        validated_data['status'] = 'new'
        instance = super().create(validated_data)
        instance._submitted_subject = subject
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Populate full_name and course_name
        ret['full_name'] = instance.candidate_name
        ret['course_name'] = instance.topic

        # Extract subject and message
        if hasattr(instance, '_submitted_subject') and instance._submitted_subject:
            ret['subject'] = instance._submitted_subject
            orig_msg = instance.message
            if orig_msg.startswith(f"{instance._submitted_subject}: "):
                ret['message'] = orig_msg[len(instance._submitted_subject) + 2:]
            elif orig_msg.startswith(f"{instance._submitted_subject}:"):
                ret['message'] = orig_msg[len(instance._submitted_subject) + 1:]
        elif ':' in instance.message and '\n' not in instance.message.split(':', 1)[0]:
            parts = instance.message.split(':', 1)
            if len(parts[0].strip()) <= 100:
                ret['subject'] = parts[0].strip()
                ret['message'] = parts[1].strip()
        else:
            ret['subject'] = ret.get('subject') or instance.topic

        # Remove internal aliases from output
        for field in ['candidate_name', 'name', 'topic', 'programme_interest']:
            ret.pop(field, None)
        return ret


class EnquiryAdminSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='candidate_name', read_only=True)
    course_name = serializers.CharField(source='topic', read_only=True)
    subject = serializers.CharField(source='inquiry_subject', read_only=True)
    message = serializers.CharField(source='original_message_body', read_only=True)
    received = serializers.SerializerMethodField()

    class Meta:
        model = Enquiry
        fields = (
            'id', 'full_name', 'email', 'phone', 'course_name',
            'subject', 'message', 'status',
            'is_active', 'is_deleted',
            'received', 'created_at', 'updated_at'
        )
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'status': {'required': False}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if not ret.get('subject'):
            ret['subject'] = instance.inquiry_subject or instance.topic
        if not ret.get('message'):
            ret['message'] = instance.original_message_body or instance.message

        # Pop any unwanted legacy keys
        for field in [
            'candidate_name', 'topic', 'programme_interest', 'topic_course',
            'inquiry_subject', 'original_message', 'message_snippet',
            'status_display', 'received_date_formatted', 'logged_date_display',
            'received_at'
        ]:
            ret.pop(field, None)
        return ret

    def validate_status(self, value):
        valid_statuses = [choice[0] for choice in Enquiry.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status '{value}'. Allowed: {valid_statuses}")
        return value

    @extend_schema_field(serializers.CharField())
    def get_received(self, obj):
        if obj.created_at:
            day = obj.created_at.strftime('%d').lstrip('0')
            month = obj.created_at.strftime('%b')
            if month == 'Sep':
                month = 'Sept'
            return f"{day} {month} {obj.created_at.strftime('%Y')}"
        return ""
        return f"Logged {date_str}" if date_str else ""


class EnquiryStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Enquiry.STATUS_CHOICES, help_text="Lead status: new, contacted, resolved")


class EnquiryStatsSummarySerializer(serializers.Serializer):
    all = serializers.IntegerField()
    new = serializers.IntegerField()
    contacted = serializers.IntegerField()
    resolved = serializers.IntegerField()


class EnquiryStatsResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    all = serializers.IntegerField()
    new = serializers.IntegerField()
    contacted = serializers.IntegerField()
    resolved = serializers.IntegerField()
    summary = EnquiryStatsSummarySerializer()


class EnquiryReplySerializer(serializers.Serializer):
    subject = serializers.CharField(required=False, default="")
    message = serializers.CharField(required=True)


class EnquiryReplyResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    enquiry = EnquiryAdminSerializer()


class EnquiryStatusChangeResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    enquiry = EnquiryAdminSerializer()

