from django.db import models
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.courses.models import Course
from apps.categories.models import Category
from api.v1.categories.serializers import CategorySerializer

class CourseListSerializer(serializers.ModelSerializer):
    category_title = serializers.CharField(source='category.title', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    fee_formatted = serializers.SerializerMethodField()
    schedule_display = serializers.SerializerMethodField()
    faculty_display = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            'id', 'title', 'slug', 'category', 'category_title', 'category_slug',
            'overview_description', 'summary', 'duration', 'level', 'fee', 'currency',
            'fee_formatted', 'schedule_display', 'learning_mode',
            'cover_image', 'modules_count', 'highlights_count', 'rating',
            'reviews_count', 'faculty_name', 'faculty_title', 'faculty_qualification',
            'faculty_experience', 'faculty_display', 'weekly_session_commitment',
            'faqs', 'is_featured', 'is_published', 'is_active', 'is_deleted',
            'created_at'
        )

    @extend_schema_field(serializers.CharField())
    def get_fee_formatted(self, obj):
        curr = obj.currency or '£'
        fee_str = f"{curr}{int(obj.fee)}" if obj.fee == int(obj.fee) else f"{curr}{obj.fee:.2f}"
        return fee_str

    @extend_schema_field(serializers.CharField())
    def get_schedule_display(self, obj):
        parts = []
        if obj.duration:
            parts.append(obj.duration)
        if obj.learning_mode:
            parts.append(obj.learning_mode.strip().capitalize())
        return " • ".join(parts)

    @extend_schema_field(serializers.CharField())
    def get_faculty_display(self, obj):
        name = obj.faculty_name or ''
        qual = obj.faculty_qualification or obj.faculty_title or ''
        if name and qual:
            return f"{name} ({qual})"
        return name or qual


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
    faqs = serializers.JSONField(required=False, default=list)
    fee_formatted = serializers.SerializerMethodField()
    schedule_display = serializers.SerializerMethodField()
    faculty_display = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            'id', 'title', 'slug', 'category', 'category_id', 'overview_description', 'summary',
            'duration', 'level', 'fee', 'currency', 'fee_formatted', 'schedule_display',
            'learning_mode', 'cover_image',
            'highlights', 'eligibility_criteria', 'eligibility_note', 'course_outcomes',
            'faqs', 'meta_description', 'meta_keywords',
            'faculty_name', 'faculty_title', 'faculty_qualification', 'faculty_experience',
            'faculty_display', 'faculty_bio', 'faculty_image',
            'curriculum', 'weekly_session_commitment', 'schedule_details',
            'modules_count', 'highlights_count', 'rating', 'reviews_count',
            'enrolled_count', 'is_published', 'is_featured', 'is_active', 'is_deleted',
            'created_at', 'updated_at'
        )

    @extend_schema_field(serializers.CharField())
    def get_fee_formatted(self, obj):
        curr = obj.currency or '£'
        fee_str = f"{curr}{int(obj.fee)}" if obj.fee == int(obj.fee) else f"{curr}{obj.fee:.2f}"
        return fee_str

    @extend_schema_field(serializers.CharField())
    def get_schedule_display(self, obj):
        parts = []
        if obj.duration:
            parts.append(obj.duration)
        if obj.learning_mode:
            parts.append(obj.learning_mode.strip().capitalize())
        return " • ".join(parts)

    @extend_schema_field(serializers.CharField())
    def get_faculty_display(self, obj):
        name = obj.faculty_name or ''
        qual = obj.faculty_qualification or obj.faculty_title or ''
        if name and qual:
            return f"{name} ({qual})"
        return name or qual


class CourseWriteSerializer(serializers.ModelSerializer):
    highlights = serializers.JSONField(required=False, default=list)
    eligibility_criteria = serializers.JSONField(required=False, default=list)
    course_outcomes = serializers.JSONField(required=False, default=list)
    meta_keywords = serializers.JSONField(required=False, default=list)
    curriculum = serializers.JSONField(required=False, default=list)
    faqs = serializers.JSONField(required=False, default=list)

    class Meta:
        model = Course
        fields = '__all__'
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'is_published': {'default': True, 'required': False},
            'overview_description': {'required': False, 'allow_blank': True},
            'eligibility_note': {'required': False, 'allow_blank': True},
            'weekly_session_commitment': {'required': False, 'allow_blank': True},
            'faculty_qualification': {'required': False, 'allow_blank': True},
            'faculty_experience': {'required': False, 'allow_blank': True},
        }

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = data.copy()

        # 1. Title alias (e.g. Programme Title)
        if not data.get('title'):
            for alias in ['programme_title', 'course_title', 'name', 'course_name']:
                if data.get(alias):
                    data['title'] = data[alias]
                    break

        # 2. Category resolution (accepts category title string or slug or ID, or nested dict)
        cat_val = data.get('category') or data.get('category_id') or data.get('programme_category')
        if isinstance(cat_val, dict):
            cat_val = cat_val.get('title') or cat_val.get('name') or cat_val.get('id')
        if cat_val is not None and str(cat_val).strip():
            from apps.categories.models import Category
            from django.utils.text import slugify
            if isinstance(cat_val, str) and not cat_val.strip().isdigit():
                cleaned_val = cat_val.strip()
                found_cat = Category.objects.filter(
                    is_deleted=False
                ).filter(
                    models.Q(title__iexact=cleaned_val) | models.Q(slug__iexact=slugify(cleaned_val))
                ).first()
                if not found_cat:
                    raise serializers.ValidationError({
                        'category': f"Course category '{cleaned_val}' does not exist. Please add the category first using the category API."
                    })
                data['category'] = found_cat.id
            elif str(cat_val).strip().isdigit():
                cat_id = int(str(cat_val).strip())
                found_cat = Category.objects.filter(id=cat_id, is_deleted=False).first()
                if not found_cat:
                    raise serializers.ValidationError({
                        'category': f"Course category with ID {cat_id} does not exist. Please add the category first using the category API."
                    })
                data['category'] = found_cat.id
        elif not getattr(self, 'partial', False):
            raise serializers.ValidationError({
                'category': "Course category is required. Please select an existing category or add it first."
            })

        # 3. Summary alias (Course Short Description / Hero Subtitle)
        if not data.get('summary'):
            for alias in ['short_description', 'hero_subtitle', 'subtitle', 'course_short_description']:
                if data.get(alias):
                    data['summary'] = data[alias]
                    break

        # 4. Overview Description (COURSE OVERVIEW CONTENT / WHAT THIS PROGRAMME COVERS)
        if not data.get('overview_description'):
            for alias in ['course_overview_content', 'overview_content', 'course_overview', 'overview', 'description']:
                if data.get(alias):
                    data['overview_description'] = data[alias]
                    break

        # 5. Eligibility note alias (Eligibility Subheading / Audience Description)
        if not data.get('eligibility_note'):
            for alias in ['eligibility_subheading', 'audience_description', 'eligibility_notes', 'note', 'notes']:
                if data.get(alias):
                    data['eligibility_note'] = data[alias]
                    break

        # 6. Highlights 4 points aggregation if submitted as separate fields
        if not data.get('highlights'):
            hl_points = []
            for key in ['highlight_point_01', 'highlight_point_02', 'highlight_point_03', 'highlight_point_04',
                        'highlight_1', 'highlight_2', 'highlight_3', 'highlight_4', 'point_1', 'point_2', 'point_3', 'point_4']:
                if data.get(key):
                    hl_points.append(str(data[key]).strip())
            if hl_points:
                data['highlights'] = hl_points

        # 7. Level normalization (e.g. 'Advanced Level' -> 'Advanced')
        if data.get('level'):
            lvl = str(data['level']).strip()
            for choice, label in Course.LEVEL_CHOICES:
                if choice.lower() in lvl.lower():
                    data['level'] = choice
                    break

        # 8. Fee normalization (strip currency symbols £, $ if passed)
        if data.get('fee') is not None:
            raw_fee = str(data['fee']).replace('£', '').replace('$', '').replace(',', '').strip()
            data['fee'] = raw_fee

        # 9. Learning mode normalization
        if data.get('learning_mode'):
            lm = str(data['learning_mode']).strip().lower()
            if 'live' in lm and 'recorded' in lm:
                data['learning_mode'] = 'live online+recorded'
            elif 'recorded' in lm:
                data['learning_mode'] = 'recorded'
            elif 'live' in lm:
                data['learning_mode'] = 'live online'

        # 10. Cover image alias
        if not data.get('cover_image'):
            for alias in ['image', 'cover', 'photo', 'programme_cover_image']:
                if data.get(alias):
                    data['cover_image'] = data[alias]
                    break

        # 11. Faculty aliases
        if not data.get('faculty_name'):
            for alias in ['faculty_full_name', 'instructor_name']:
                if data.get(alias):
                    data['faculty_name'] = data[alias]
                    break

        if not data.get('faculty_qualification') and not data.get('faculty_title'):
            for alias in ['faculty_qualification', 'qualification', 'faculty_title']:
                if data.get(alias):
                    data['faculty_qualification'] = data[alias]
                    data['faculty_title'] = data[alias]
                    break

        if not data.get('faculty_experience'):
            for alias in ['experience', 'years_of_experience']:
                if data.get(alias):
                    data['faculty_experience'] = data[alias]
                    break

        if not data.get('faculty_bio'):
            for alias in ['faculty_description', 'instructor_bio']:
                if data.get(alias):
                    data['faculty_bio'] = data[alias]
                    break

        if not data.get('faculty_image'):
            for alias in ['faculty_portrait', 'faculty_photo', 'instructor_photo']:
                if data.get(alias):
                    data['faculty_image'] = data[alias]
                    break

        # 12. Schedule & Commitment aliases
        if not data.get('weekly_session_commitment'):
            for alias in ['weekly_commitment', 'session_commitment', 'commitment']:
                if data.get(alias):
                    data['weekly_session_commitment'] = data[alias]
                    break

        if not data.get('schedule_details'):
            for alias in ['schedule_summary_narrative', 'schedule_summary', 'schedule_narrative']:
                if data.get(alias):
                    data['schedule_details'] = data[alias]
                    break

        # 13. Outcomes alias
        if not data.get('course_outcomes'):
            for alias in ['learning_outcomes', 'outcomes', 'key_competencies']:
                if data.get(alias):
                    data['course_outcomes'] = data[alias]
                    break

        # 14. Curriculum alias
        if not data.get('curriculum'):
            for alias in ['modules', 'syllabus']:
                if data.get(alias):
                    data['curriculum'] = data[alias]
                    break

        # 15. FAQs alias
        if not data.get('faqs') and data.get('faq'):
            data['faqs'] = data['faq']

        return super().to_internal_value(data)

    def validate(self, attrs):
        if not attrs.get('category') and not (self.instance and self.instance.category_id):
            raise serializers.ValidationError({
                'category': 'Course category is required. A category must be created or selected before adding a course.'
            })
        return attrs


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


class FacultyItemSerializer(serializers.Serializer):
    faculty_name = serializers.CharField()
    faculty_title = serializers.CharField()
    faculty_qualification = serializers.CharField()
    faculty_experience = serializers.CharField()
    faculty_bio = serializers.CharField()
    faculty_display = serializers.CharField()
    faculty_image = serializers.CharField(allow_null=True)


class FacultyListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = FacultyItemSerializer(many=True)
