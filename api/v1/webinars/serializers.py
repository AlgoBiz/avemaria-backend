import uuid
import datetime
from django.db import models
from django.utils.text import slugify
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.webinars.models import Webinar
from apps.faculty.models import Faculty


class SpeakerNestedSerializer(serializers.ModelSerializer):
    """
    Nested serializer for Speaker faculty details.
    Produces:
    {
        "id": "<faculty_uuid>",
        "name": "<faculty_name>"
    }
    """
    id = serializers.CharField(source='uuid_str', read_only=True)
    name = serializers.CharField(read_only=True)

    class Meta:
        model = Faculty
        fields = ('id', 'name')


class WebinarSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for Webinar/Workshop entities.
    Supports GET, POST, PUT, PATCH operations.
    Handles nested speaker retrieval and flexible speaker assignment by ID/UUID.
    """
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    speaker = SpeakerNestedSerializer(read_only=True)
    speaker_id = serializers.CharField(write_only=True, required=False, allow_null=True)
    scheduled_date = serializers.DateField(
        format='%d/%m/%Y',
        input_formats=['%d/%m/%Y', '%d/%m//%Y', '%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d'],
        required=False,
        allow_null=True
    )
    date = serializers.SerializerMethodField(read_only=True)
    cover_image = serializers.FileField(required=False, allow_null=True)
    cover_image_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_expired = serializers.BooleanField(read_only=True)
    event_status = serializers.CharField(read_only=True)

    class Meta:
        model = Webinar
        fields = (
            'id',
            'type',
            'title',
            'slug',
            'scheduled_date',
            'date',
            'timing',
            'platform',
            'speaker',
            'speaker_id',
            'registration_url',
            'summary_description',
            'outline_agenda',
            'cover_image',
            'cover_image_url',
            'status',
            'event_status',
            'is_expired',
            'is_active',
            'is_deleted',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'slug', 'date', 'is_expired', 'event_status', 'created_at', 'updated_at')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_date(self, obj):
        if obj.scheduled_date:
            return obj.scheduled_date.strftime('%d/%m/%Y')
        return None

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Ensure scheduled_date and date are in DD/MM/YYYY format
        if instance.scheduled_date:
            formatted_date = instance.scheduled_date.strftime('%d/%m/%Y')
            ret['scheduled_date'] = formatted_date
            ret['date'] = formatted_date
        else:
            ret['scheduled_date'] = None
            ret['date'] = None

        # Ensure cover_image URL is absolute in representation
        if instance.cover_image:
            request = self.context.get('request')
            if request:
                ret['cover_image'] = request.build_absolute_uri(instance.cover_image.url)
            else:
                ret['cover_image'] = instance.cover_image.url
        else:
            ret['cover_image'] = None

        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)

        # Normalize status to 'published' or 'draft'
        if ret.get('status') in ['publish', 'published']:
            ret['status'] = 'published'
        elif ret.get('status') in ['draft', 'unpublished']:
            ret['status'] = 'draft'

        return ret

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        # Normalize type (webinar vs workshop)
        raw_type = mutable_data.get('type')
        if raw_type is not None:
            cleaned_type = str(raw_type).strip().lower()
            if cleaned_type in ['webinar', 'webinars']:
                mutable_data['type'] = Webinar.TYPE_WEBINAR
            elif cleaned_type in ['workshop', 'workshops']:
                mutable_data['type'] = Webinar.TYPE_WORKSHOP
            else:
                mutable_data['type'] = cleaned_type

        # Normalize status (published vs draft)
        raw_status = mutable_data.get('status')
        if raw_status is not None:
            cleaned_status = str(raw_status).strip().lower()
            if cleaned_status in ['publish', 'published', 'active']:
                mutable_data['status'] = Webinar.STATUS_PUBLISHED
            elif cleaned_status in ['draft', 'unpublished', 'inactive']:
                mutable_data['status'] = Webinar.STATUS_DRAFT
            else:
                mutable_data['status'] = cleaned_status

        # Aliases for timing
        if not mutable_data.get('timing'):
            for alias in ['time', 'scheduled_time', 'event_timing', 'session_timing']:
                if mutable_data.get(alias):
                    mutable_data['timing'] = mutable_data[alias]
                    break

        # Aliases for platform
        if not mutable_data.get('platform'):
            for alias in ['venue', 'meeting_platform', 'event_platform', 'location']:
                if mutable_data.get(alias):
                    mutable_data['platform'] = mutable_data[alias]
                    break

        # Aliases for registration_url
        if not mutable_data.get('registration_url'):
            for alias in ['registration_link', 'register_url', 'join_url', 'join_link']:
                if mutable_data.get(alias):
                    mutable_data['registration_url'] = mutable_data[alias]
                    break

        # Aliases for summary_description
        if not mutable_data.get('summary_description'):
            for alias in ['description', 'summary', 'short_description', 'overview']:
                if mutable_data.get(alias):
                    mutable_data['summary_description'] = mutable_data[alias]
                    break

        # Aliases for outline_agenda & handling lists
        if not mutable_data.get('outline_agenda'):
            for alias in ['agenda', 'outline', 'agenda_points', 'syllabus']:
                if mutable_data.get(alias):
                    mutable_data['outline_agenda'] = mutable_data[alias]
                    break

        agenda_val = mutable_data.get('outline_agenda')
        if isinstance(agenda_val, str) and agenda_val.strip():
            raise serializers.ValidationError({'outline_agenda': 'outline_agenda must be an array, e.g. ["Point 1", "Point 2"]'})
        elif isinstance(agenda_val, dict):
            raise serializers.ValidationError({'outline_agenda': 'outline_agenda must be an array, e.g. ["Point 1", "Point 2"]'})

        # Parse speaker input: accept speaker as int ID, UUID string, or object {"id": ...}
        raw_speaker = mutable_data.get('speaker')
        if raw_speaker is not None and not mutable_data.get('speaker_id'):
            if isinstance(raw_speaker, dict):
                mutable_data['speaker_id'] = raw_speaker.get('id') or raw_speaker.get('uuid') or raw_speaker.get('speaker_id')
            elif isinstance(raw_speaker, (int, str)):
                mutable_data['speaker_id'] = raw_speaker
        if 'speaker' in mutable_data and isinstance(mutable_data['speaker'], (dict, int, str)):
            # remove non-field speaker dict from DRF direct model assignment
            mutable_data.pop('speaker')

        # Cover image url alias
        if not mutable_data.get('cover_image_url'):
            for alias in ['image_url', 'thumbnail_url', 'banner_url']:
                if mutable_data.get(alias):
                    mutable_data['cover_image_url'] = mutable_data[alias]
                    break

        # Aliases for scheduled_date (e.g. 'date', 'event_date', 'session_date')
        if not mutable_data.get('scheduled_date'):
            for alias in ['date', 'event_date', 'session_date', 'webinar_date']:
                if mutable_data.get(alias):
                    mutable_data['scheduled_date'] = mutable_data[alias]
                    break

        # Parse scheduled_date formats with support for DD/MM/YYYY and DD/MM//YYYY
        pdate = mutable_data.get('scheduled_date')
        if pdate and isinstance(pdate, str):
            pdate_str = pdate.strip()
            # If ISO datetime with 'T', extract the date portion
            if 'T' in pdate_str:
                pdate_str = pdate_str.split('T')[0]
            # Normalize multiple consecutive slashes (e.g. '15/11//2026' or 'dd/mm//yyyy') to single slash
            import re
            cleaned_pdate_str = re.sub(r'/+', '/', pdate_str)
            formats = ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d %B %Y', '%d %b %Y', '%B %d, %Y', '%Y/%m/%d')
            for fmt in formats:
                try:
                    dt = datetime.datetime.strptime(cleaned_pdate_str, fmt)
                    mutable_data['scheduled_date'] = dt.date().strftime('%d/%m/%Y')
                    break
                except ValueError:
                    continue

        return super().to_internal_value(mutable_data)

    def validate_type(self, value):
        if value not in [Webinar.TYPE_WEBINAR, Webinar.TYPE_WORKSHOP]:
            raise serializers.ValidationError(f"Type must be either '{Webinar.TYPE_WEBINAR}' or '{Webinar.TYPE_WORKSHOP}'.")
        return value

    def validate_status(self, value):
        if value not in [Webinar.STATUS_PUBLISHED, Webinar.STATUS_DRAFT, 'publish']:
            raise serializers.ValidationError(f"Status must be either '{Webinar.STATUS_PUBLISHED}' or '{Webinar.STATUS_DRAFT}'.")
        return Webinar.STATUS_PUBLISHED if value in [Webinar.STATUS_PUBLISHED, 'publish'] else Webinar.STATUS_DRAFT

    def validate(self, attrs):
        title = attrs.get('title') or (self.instance and self.instance.title)
        if not title or not str(title).strip():
            raise serializers.ValidationError({'title': 'Webinar title is required.'})

        cleaned_title = ' '.join(str(title).strip().split())
        attrs['title'] = cleaned_title

        title_slug = slugify(cleaned_title)
        existing_qs = Webinar.objects.filter(is_deleted=False).filter(
            models.Q(title__iexact=cleaned_title) | models.Q(slug__iexact=title_slug)
        )
        if self.instance:
            existing_qs = existing_qs.exclude(pk=self.instance.pk)

        if existing_qs.exists():
            raise serializers.ValidationError({
                'title': f"A webinar or workshop with the title '{cleaned_title}' already exists."
            })

        return attrs

    def _resolve_speaker(self, speaker_identifier):
        if not speaker_identifier:
            return None
        s_val = str(speaker_identifier).strip()
        if not s_val or s_val.lower() in ['none', 'null', '']:
            return None

        # Check integer ID
        if s_val.isdigit():
            fac = Faculty.objects.filter(id=int(s_val), is_deleted=False).first()
            if fac:
                return fac

        # Check UUID
        try:
            val_uuid = uuid.UUID(s_val)
            fac = Faculty.objects.filter(uuid=val_uuid, is_deleted=False).first()
            if fac:
                return fac
        except (ValueError, TypeError):
            pass

        # Check by name
        fac = Faculty.objects.filter(name__iexact=s_val, is_deleted=False).first()
        if fac:
            return fac

        raise serializers.ValidationError({"speaker_id": f"Faculty speaker with identifier '{speaker_identifier}' does not exist."})

    def create(self, validated_data):
        speaker_id = validated_data.pop('speaker_id', None)
        raw_data = self.initial_data if hasattr(self, 'initial_data') and self.initial_data else {}

        # If speaker_id wasn't in validated_data, check raw_data
        if speaker_id is None and 'speaker_id' in raw_data:
            speaker_id = raw_data.get('speaker_id')
        elif speaker_id is None and 'speaker' in raw_data:
            spk = raw_data.get('speaker')
            speaker_id = spk.get('id') if isinstance(spk, dict) else spk

        if speaker_id:
            validated_data['speaker'] = self._resolve_speaker(speaker_id)

        # File upload handling from request
        request = self.context.get('request')
        if request and request.FILES:
            cover_file = request.FILES.get('cover_image') or request.FILES.get('image') or request.FILES.get('file')
            if cover_file:
                validated_data['cover_image'] = cover_file

        return super().create(validated_data)

    def update(self, instance, validated_data):
        raw_data = self.initial_data if hasattr(self, 'initial_data') and self.initial_data else {}
        has_speaker_key = 'speaker_id' in validated_data or 'speaker_id' in raw_data or 'speaker' in raw_data

        if has_speaker_key:
            speaker_val = validated_data.pop('speaker_id', None)
            if speaker_val is None and 'speaker_id' in raw_data:
                speaker_val = raw_data.get('speaker_id')
            elif speaker_val is None and 'speaker' in raw_data:
                spk = raw_data.get('speaker')
                speaker_val = spk.get('id') if isinstance(spk, dict) else spk

            if speaker_val in [None, '', 'null', 'None']:
                instance.speaker = None
            else:
                instance.speaker = self._resolve_speaker(speaker_val)

        # File upload handling from request
        request = self.context.get('request')
        if request and request.FILES:
            cover_file = request.FILES.get('cover_image') or request.FILES.get('image') or request.FILES.get('file')
            if cover_file:
                validated_data['cover_image'] = cover_file

        return super().update(instance, validated_data)


class WebinarListSerializer(serializers.ModelSerializer):
    """
    Serializer for webinars & workshops list views matching the exact schema.
    """
    id = serializers.CharField(source='uuid_str', read_only=True)
    speaker = SpeakerNestedSerializer(read_only=True)
    scheduled_date = serializers.DateField(format='%d/%m/%Y', required=False, allow_null=True)
    date = serializers.SerializerMethodField(read_only=True)
    cover_image = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    event_status = serializers.CharField(read_only=True)

    class Meta:
        model = Webinar
        fields = (
            'id',
            'type',
            'title',
            'slug',
            'scheduled_date',
            'date',
            'timing',
            'platform',
            'speaker',
            'registration_url',
            'summary_description',
            'outline_agenda',
            'cover_image',
            'cover_image_url',
            'status',
            'event_status',
            'is_expired',
            'is_active',
            'is_deleted',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'slug', 'date', 'is_expired', 'event_status', 'created_at', 'updated_at')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_date(self, obj):
        if obj.scheduled_date:
            return obj.scheduled_date.strftime('%d/%m/%Y')
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cover_image(self, obj):
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Ensure scheduled_date and date are in DD/MM/YYYY format
        if instance.scheduled_date:
            formatted_date = instance.scheduled_date.strftime('%d/%m/%Y')
            ret['scheduled_date'] = formatted_date
            ret['date'] = formatted_date
        else:
            ret['scheduled_date'] = None
            ret['date'] = None

        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        if ret.get('status') in ['publish', 'published']:
            ret['status'] = 'published'
        elif ret.get('status') in ['draft', 'unpublished']:
            ret['status'] = 'draft'
        return ret


class WebinarStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    webinars_count = serializers.IntegerField()
    workshops_count = serializers.IntegerField()
    published_count = serializers.IntegerField()
    draft_count = serializers.IntegerField()
    upcoming_count = serializers.IntegerField()
    summary_display = serializers.CharField()


class WebinarToggleStatusResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    status = serializers.CharField()
    is_published = serializers.BooleanField()
    message = serializers.CharField()
