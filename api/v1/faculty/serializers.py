from django.db import models
from django.utils.text import slugify
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.faculty.models import Faculty


class FacultySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    faculty_display = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    specialities = serializers.JSONField(required=False, default=list)
    status = serializers.ChoiceField(choices=['active', 'inactive'], default='active', required=False)

    class Meta:
        model = Faculty
        fields = (
            'id',
            'slug',
            'name',
            'title',
            'qualification',
            'experience',
            'department',
            'specialities',
            'bio',
            'image',
            'email',
            'phone',
            'status',
            'is_published',
            'is_featured',
            'display_order',
            'faculty_display',
            'initials',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'slug', 'faculty_display', 'initials', 'created_at', 'updated_at')

    def validate(self, attrs):
        # 1. Validate Name Uniqueness
        name = attrs.get('name') or (self.instance and self.instance.name)
        if not name or not str(name).strip():
            raise serializers.ValidationError({'name': 'Faculty name is required.'})

        cleaned_name = ' '.join(str(name).strip().split())
        attrs['name'] = cleaned_name

        name_slug = slugify(cleaned_name)
        name_qs = Faculty.objects.filter(is_deleted=False).filter(
            models.Q(name__iexact=cleaned_name) | models.Q(slug__iexact=name_slug)
        )
        if self.instance:
            name_qs = name_qs.exclude(pk=self.instance.pk)

        if name_qs.exists():
            raise serializers.ValidationError({
                'name': f"A faculty member with the name '{cleaned_name}' already exists."
            })

        # 2. Validate Email Uniqueness (if email is provided)
        email = attrs.get('email') or (self.instance and self.instance.email)
        if email and str(email).strip():
            cleaned_email = str(email).strip().lower()
            attrs['email'] = cleaned_email

            email_qs = Faculty.objects.filter(
                email__iexact=cleaned_email,
                is_deleted=False
            )
            if self.instance:
                email_qs = email_qs.exclude(pk=self.instance.pk)

            if email_qs.exists():
                raise serializers.ValidationError({
                    'email': f"A faculty member with the email '{cleaned_email}' already exists."
                })

        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        if hasattr(instance, 'slug'):
            ret['slug'] = instance.slug
        return ret


class FacultyListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    faculty_display = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    specialities = serializers.JSONField(required=False, default=list)
    status = serializers.ChoiceField(choices=['active', 'inactive'], default='active', required=False)

    class Meta:
        model = Faculty
        fields = (
            'id',
            'slug',
            'name',
            'title',
            'qualification',
            'experience',
            'department',
            'specialities',
            'bio',
            'image',
            'status',
            'is_published',
            'is_featured',
            'display_order',
            'faculty_display',
            'initials'
        )

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        if hasattr(instance, 'slug'):
            ret['slug'] = instance.slug
        return ret


class FacultyMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer returning only id, name, qualification, description, and image."""
    id = serializers.CharField(source='uuid_str', read_only=True)
    description = serializers.CharField(source='bio', read_only=True, allow_null=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Faculty
        fields = (
            'id',
            'name',
            'qualification',
            'description',
            'image',
        )

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        return ret

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class FacultyStatsSerializer(serializers.Serializer):
    total_faculties = serializers.IntegerField(required=False)
    active_faculties = serializers.IntegerField(required=False)
    total_covered_courses = serializers.IntegerField(required=False)
    total = serializers.IntegerField(required=False)
    published = serializers.IntegerField(required=False)
    featured = serializers.IntegerField(required=False)
    departments_count = serializers.IntegerField(required=False)
    stats = serializers.DictField(required=False)
