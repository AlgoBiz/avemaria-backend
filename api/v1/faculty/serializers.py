from rest_framework import serializers
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



class FacultyStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    published = serializers.IntegerField()
    featured = serializers.IntegerField()
    departments_count = serializers.IntegerField()
