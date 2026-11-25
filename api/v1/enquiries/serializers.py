import uuid
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.enquiries.models import Enquiry
from apps.enquiries.emails import send_enquiry_notification_email
from apps.faculty.models import Faculty


def _resolve_faculty(value):
    """Resolve a Faculty instance from UUID, integer ID, slug, or name."""
    if not value:
        return None
    if isinstance(value, Faculty):
        return value
    val_str = str(value).strip()
    if not val_str:
        return None
    qs = Faculty.objects.filter(is_deleted=False)
    try:
        u = uuid.UUID(val_str)
        obj = qs.filter(uuid=u).first()
        if obj:
            return obj
    except (ValueError, TypeError):
        pass
    if val_str.isdigit():
        obj = qs.filter(id=int(val_str)).first()
        if obj:
            return obj
    obj = qs.filter(slug__iexact=val_str).first()
    if obj:
        return obj
    return qs.filter(name__iexact=val_str).first()


class EnquiryCreateSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    full_name = serializers.CharField(required=False)
    course_name = serializers.CharField(required=False)
    subject = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)

    enquiry_type = serializers.CharField(required=False, allow_blank=True, default='')
    faculty = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    faculty_name = serializers.CharField(required=False, allow_blank=True, default='')
    custom_requirement = serializers.CharField(required=False, allow_blank=True, default='')
    routed_to_email = serializers.EmailField(read_only=True)

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
            'id', 'slug', 'full_name', 'email', 'phone',
            'course_name', 'enquiry_type', 'faculty', 'faculty_name',
            'custom_requirement', 'routed_to_email',
            'subject', 'message',
            'candidate_name', 'name', 'topic', 'programme_interest',
            'status', 'status_display', 'created_at'
        )
        read_only_fields = ('id', 'slug', 'routed_to_email', 'created_at')
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

        # Enquiry type aliases
        if not data.get('enquiry_type'):
            for alias in ['inquiry_type', 'type', 'department', 'enquiry_category', 'sub_category', 'sub_type']:
                if data.get(alias):
                    data['enquiry_type'] = data[alias]
                    break

        # Faculty aliases
        if not data.get('faculty'):
            for alias in ['faculty_id', 'mentor', 'mentor_id']:
                if data.get(alias):
                    data['faculty'] = data[alias]
                    break
        if not data.get('faculty_name'):
            for alias in ['mentor_name']:
                if data.get(alias):
                    data['faculty_name'] = data[alias]
                    break

        # Custom requirement aliases
        if not data.get('custom_requirement'):
            for alias in ['requirement', 'specify_requirement', 'custom_course', 'other_requirement', 'specify']:
                if data.get(alias):
                    data['custom_requirement'] = data[alias]
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
        faculty_raw = validated_data.pop('faculty', None)

        if not validated_data.get('candidate_name') and full_name:
            validated_data['candidate_name'] = full_name

        if not validated_data.get('topic'):
            if course_name:
                validated_data['topic'] = course_name
            elif programme_interest:
                validated_data['topic'] = programme_interest
            else:
                validated_data['topic'] = 'Licensing preparation'

        # Resolve faculty from UUID / ID / slug / name (fallback to faculty_name if needed)
        faculty_obj = _resolve_faculty(faculty_raw) or _resolve_faculty(validated_data.get('faculty_name'))
        if faculty_obj:
            validated_data['faculty'] = faculty_obj
            if not validated_data.get('faculty_name'):
                validated_data['faculty_name'] = faculty_obj.name
        elif faculty_raw and not validated_data.get('faculty_name'):
            validated_data['faculty_name'] = str(faculty_raw).strip()

        # Infer enquiry_type if omitted but topic itself is a known department type
        if not validated_data.get('enquiry_type'):
            topic_lower = str(validated_data.get('topic', '')).strip().lower()
            if topic_lower in {
                'general enquiry', 'general', 'admission', 'admissions',
                'support', 'payment', 'payments', 'complaints', 'complaint',
                'privacy', 'faculty'
            }:
                validated_data['enquiry_type'] = validated_data['topic']

        if subject:
            original_msg = validated_data.get('message', '')
            if not original_msg.startswith(f"{subject}:"):
                validated_data['message'] = f"{subject}: {original_msg}"

        validated_data['status'] = 'new'
        instance = super().create(validated_data)
        instance._submitted_subject = subject
        send_enquiry_notification_email(instance)
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = str(instance.uuid)
        ret['slug'] = instance.slug
        # Populate full_name and course_name
        ret['full_name'] = instance.candidate_name
        ret['course_name'] = instance.topic
        ret['enquiry_type'] = instance.enquiry_type
        ret['faculty_id'] = str(instance.faculty.uuid) if instance.faculty else None
        ret['faculty_name'] = instance.faculty_name or (instance.faculty.name if instance.faculty else '')
        ret['custom_requirement'] = instance.custom_requirement
        ret['routed_to_email'] = instance.routed_to_email

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
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    full_name = serializers.CharField(source='candidate_name', read_only=True)
    course_name = serializers.CharField(source='topic', read_only=True)
    subject = serializers.CharField(source='inquiry_subject', read_only=True)
    message = serializers.CharField(source='original_message_body', read_only=True)
    received = serializers.SerializerMethodField()

    class Meta:
        model = Enquiry
        fields = (
            'id', 'slug', 'full_name', 'email', 'phone', 'course_name',
            'enquiry_type', 'faculty_name', 'custom_requirement', 'routed_to_email',
            'subject', 'message', 'status',
            'is_active', 'is_deleted',
            'received', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'slug', 'received', 'routed_to_email', 'created_at', 'updated_at')
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'status': {'required': False}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = str(instance.uuid)
        ret['slug'] = instance.slug
        ret['faculty_id'] = str(instance.faculty.uuid) if instance.faculty else None
        ret['faculty_name'] = instance.faculty_name or (instance.faculty.name if instance.faculty else '')
        if not ret.get('subject'):
            ret['subject'] = instance.inquiry_subject or instance.topic
        if not ret.get('message'):
            ret['message'] = instance.original_message_body or instance.message

        ret['candidate_name'] = instance.candidate_name
        ret['topic'] = instance.topic
        ret['topic_course'] = instance.topic

        status_map = {'new': 'New Lead', 'contacted': 'Contacted', 'resolved': 'Enrolled'}
        ret['status_display'] = status_map.get(instance.status, str(instance.status).title())
        msg = instance.message or instance.original_message_body or ''
        ret['message_snippet'] = msg[:120]

        # Pop any unwanted legacy keys
        for field in [
            'programme_interest',
            'inquiry_subject', 'original_message',
            'received_date_formatted', 'logged_date_display',
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

