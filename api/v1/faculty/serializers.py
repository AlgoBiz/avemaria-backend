from rest_framework import serializers
from apps.faculty.models import Faculty


class FacultySerializer(serializers.ModelSerializer):
    faculty_display = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)

    class Meta:
        model = Faculty
        fields = (
            'id',
            'name',
            'title',
            'qualification',
            'experience',
            'department',
            'bio',
            'image',
            'email',
            'phone',
            'is_published',
            'is_featured',
            'display_order',
            'faculty_display',
            'initials',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'faculty_display', 'initials', 'created_at', 'updated_at')


class FacultyListSerializer(serializers.ModelSerializer):
    faculty_display = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)

    class Meta:
        model = Faculty
        fields = (
            'id',
            'name',
            'title',
            'qualification',
            'experience',
            'department',
            'bio',
            'image',
            'is_published',
            'is_featured',
            'display_order',
            'faculty_display',
            'initials'
        )


class FacultyStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    published = serializers.IntegerField()
    featured = serializers.IntegerField()
    departments_count = serializers.IntegerField()
