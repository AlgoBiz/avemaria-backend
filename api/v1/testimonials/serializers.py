from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.testimonials.models import Testimonial

class TestimonialSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='programme_name', required=False, allow_blank=True)
    review = serializers.CharField(source='quote', required=False)

    class Meta:
        model = Testimonial
        fields = (
            'id', 'candidate_name', 'initials', 'course_name', 'result_placement',
            'country', 'review', 'rating', 'photo',
            'is_published', 'is_student_submission',
            'created_at', 'updated_at'
        )
        read_only_fields = ('initials', 'created_at', 'updated_at')
        extra_kwargs = {
            'candidate_name': {'required': False},
            'result_placement': {'required': False, 'allow_blank': True},
            'country': {'required': False, 'allow_blank': True},
            'photo': {'required': False},
            'is_published': {'default': True, 'required': False},
            'is_student_submission': {'default': False, 'required': False}
        }

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        # 1. Candidate name alias
        if not mutable_data.get('candidate_name'):
            for alias in ['candidate_full_name', 'full_name', 'name']:
                if mutable_data.get(alias):
                    mutable_data['candidate_name'] = mutable_data[alias]
                    break

        # 2. Course / Programme name alias
        if not mutable_data.get('course_name'):
            for alias in ['programme_name', 'programme', 'enrolled_programme', 'enrolled_course', 'course']:
                if mutable_data.get(alias):
                    mutable_data['course_name'] = str(mutable_data[alias])
                    break

        # 3. Country / City alias
        if not mutable_data.get('country'):
            for alias in ['country_city', 'city', 'location']:
                if mutable_data.get(alias):
                    mutable_data['country'] = mutable_data[alias]
                    break

        # 4. Result / Placement alias
        if not mutable_data.get('result_placement'):
            for alias in ['result', 'placement', 'outcome']:
                if mutable_data.get(alias):
                    mutable_data['result_placement'] = mutable_data[alias]
                    break

        # 5. Review / Quote alias
        if not mutable_data.get('review'):
            for alias in ['quote', 'candidate_quote', 'content', 'comment', 'testimonial']:
                if mutable_data.get(alias):
                    mutable_data['review'] = mutable_data[alias]
                    break

        # 6. Photo alias
        if not mutable_data.get('photo'):
            for alias in ['candidate_photo', 'image', 'avatar', 'picture']:
                if mutable_data.get(alias):
                    mutable_data['photo'] = mutable_data[alias]
                    break

        # 7. Publication status normalization (e.g. 'Published' -> True, 'Unpublished' -> False)
        pub_status = mutable_data.get('publication_status') or mutable_data.get('status')
        if pub_status is not None:
            if str(pub_status).strip().lower() in ['published', 'true', '1']:
                mutable_data['is_published'] = True
            elif str(pub_status).strip().lower() in ['unpublished', 'draft', 'hidden', 'false', '0']:
                mutable_data['is_published'] = False

        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        if not attrs.get('candidate_name') and not (self.instance and self.instance.candidate_name):
            raise serializers.ValidationError({'candidate_name': 'Candidate full name is required.'})
        if not attrs.get('quote') and not (self.instance and self.instance.quote):
            raise serializers.ValidationError({'review': 'Candidate review is required.'})
        return attrs


class TestimonialStatItemSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    label = serializers.CharField()


class TestimonialStatsSerializer(serializers.Serializer):
    total_reviews = TestimonialStatItemSerializer()
    published = TestimonialStatItemSerializer()
    unpublished = TestimonialStatItemSerializer()
    student_submitted = TestimonialStatItemSerializer()
