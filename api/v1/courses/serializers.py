from rest_framework import serializers
from apps.courses.models import Course
from apps.categories.models import Category
from api.v1.categories.serializers import CategorySerializer

class CourseListSerializer(serializers.ModelSerializer):
    category_title = serializers.CharField(source='category.title', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)

    class Meta:
        model = Course
        fields = (
            'id', 'title', 'slug', 'category', 'category_title', 'category_slug',
            'summary', 'duration', 'level', 'fee', 'currency', 'learning_mode',
            'cover_image', 'modules_count', 'highlights_count', 'rating',
            'reviews_count', 'faculty_name', 'is_published', 'is_active', 'is_deleted',
            'created_at'
        )

class CourseDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    highlights = serializers.JSONField(required=False, default=list)
    eligibility_criteria = serializers.JSONField(required=False, default=list)
    course_outcomes = serializers.JSONField(required=False, default=list)
    meta_keywords = serializers.JSONField(required=False, default=list)
    curriculum = serializers.JSONField(required=False, default=list)

    class Meta:
        model = Course
        fields = (
            'id', 'title', 'slug', 'category', 'category_id', 'summary',
            'duration', 'level', 'fee', 'currency', 'learning_mode', 'cover_image',
            'highlights', 'eligibility_criteria', 'course_outcomes',
            'meta_description', 'meta_keywords',
            'faculty_name', 'faculty_title', 'faculty_bio', 'faculty_image',
            'curriculum', 'schedule_details',
            'modules_count', 'highlights_count', 'rating', 'reviews_count',
            'enrolled_count', 'is_published', 'is_active', 'is_deleted',
            'created_at', 'updated_at'
        )

class CourseWriteSerializer(serializers.ModelSerializer):
    highlights = serializers.JSONField(required=False, default=list)
    eligibility_criteria = serializers.JSONField(required=False, default=list)
    course_outcomes = serializers.JSONField(required=False, default=list)
    meta_keywords = serializers.JSONField(required=False, default=list)
    curriculum = serializers.JSONField(required=False, default=list)

    class Meta:
        model = Course
        fields = '__all__'
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'is_published': {'default': True, 'required': False}
        }


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        from apps.courses.models import CourseEnrollment
        model = CourseEnrollment
        fields = (
            'id', 'course', 'status', 'status_display',
            'progress_percentage', 'enrolled_at', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'status_display', 'enrolled_at', 'created_at', 'updated_at')
