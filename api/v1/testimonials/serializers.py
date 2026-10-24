from collections import OrderedDict
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.testimonials.models import Testimonial

class TestimonialSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    course_name = serializers.CharField(source='programme_name', required=False, allow_blank=True)
    review = serializers.CharField(source='quote', required=False)
    photo = serializers.FileField(required=False, allow_null=True)
    image = serializers.FileField(source='photo', required=False, allow_null=True)

    class Meta:
        model = Testimonial
        fields = (
            'id', 'slug', 'candidate_name', 'initials', 'course_name', 'result_placement',
            'country', 'review', 'rating', 'photo', 'image',
            'is_published', 'is_student_submission',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'slug', 'initials', 'created_at', 'updated_at')
        extra_kwargs = {
            'candidate_name': {'required': False},
            'result_placement': {'required': False, 'allow_blank': True},
            'country': {'required': False, 'allow_blank': True},
            'is_published': {'default': True, 'required': False},
            'is_student_submission': {'default': False, 'required': False}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = str(instance.uuid)
        ret['slug'] = instance.slug

        request = self.context.get('request')
        image_url = None
        if instance.photo:
            image_url = request.build_absolute_uri(instance.photo.url) if request else instance.photo.url

        ordered_ret = OrderedDict()
        for field in self.Meta.fields:
            if field in ret:
                ordered_ret[field] = ret[field]
        ordered_ret['image'] = image_url
        ordered_ret['photo'] = image_url
        ordered_ret['programme_name'] = instance.programme_name
        return ordered_ret

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

        # 6. Clean null/empty string aliases for file fields
        for k in ['photo', 'image', 'candidate_photo', 'avatar']:
            if mutable_data.get(k) in ['', 'null', 'None', None]:
                mutable_data.pop(k, None)

        # 7. Check request.FILES for uploaded binary image
        request = self.context.get('request')
        if request and request.FILES:
            file_obj = (
                request.FILES.get('photo') or
                request.FILES.get('image') or
                request.FILES.get('candidate_photo') or
                request.FILES.get('avatar') or
                request.FILES.get('file')
            )
            if file_obj:
                mutable_data['photo'] = file_obj

        # 8. Check mutable_data aliases for photo
        if not mutable_data.get('photo'):
            for alias in ['candidate_photo', 'image', 'avatar', 'picture', 'candidate_image', 'file']:
                if mutable_data.get(alias):
                    mutable_data['photo'] = mutable_data[alias]
                    break

        # 9. Initials override if provided
        if mutable_data.get('initials'):
            mutable_data['initials'] = str(mutable_data['initials']).strip()

        # 10. Publication status normalization (e.g. 'Published' -> True, 'Unpublished' -> False)
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

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.FILES and not validated_data.get('photo'):
            file_obj = (
                request.FILES.get('photo') or
                request.FILES.get('image') or
                request.FILES.get('candidate_photo') or
                request.FILES.get('avatar') or
                request.FILES.get('file')
            )
            if file_obj:
                validated_data['photo'] = file_obj
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and request.FILES and not validated_data.get('photo'):
            file_obj = (
                request.FILES.get('photo') or
                request.FILES.get('image') or
                request.FILES.get('candidate_photo') or
                request.FILES.get('avatar') or
                request.FILES.get('file')
            )
            if file_obj:
                validated_data['photo'] = file_obj
        return super().update(instance, validated_data)


class TestimonialStatItemSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    label = serializers.CharField()


class TestimonialStatsSerializer(serializers.Serializer):
    total_reviews = TestimonialStatItemSerializer()
    published = TestimonialStatItemSerializer()
    unpublished = TestimonialStatItemSerializer()
    student_submitted = TestimonialStatItemSerializer()
