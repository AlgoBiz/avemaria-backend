from rest_framework import serializers
from apps.testimonials.models import Testimonial

class TestimonialSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='candidate_name', required=False)
    photo_url = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Testimonial
        fields = (
            'id', 'candidate_name', 'name', 'initials', 'result_placement',
            'country', 'quote', 'rating', 'photo', 'photo_url', 'avatar',
            'is_featured', 'is_active', 'is_deleted', 'created_at', 'updated_at'
        )
        read_only_fields = ('initials', 'created_at', 'updated_at')
        extra_kwargs = {
            'candidate_name': {'required': False},
            'result_placement': {'required': False},
            'country': {'required': False},
            'photo': {'required': False},
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'is_featured': {'default': True, 'required': False}
        }

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

    def get_avatar(self, obj):
        return self.get_photo_url(obj)

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        # Support 'name' or 'full_name' alias for 'candidate_name'
        if not mutable_data.get('candidate_name'):
            if mutable_data.get('name'):
                mutable_data['candidate_name'] = mutable_data['name']
            elif mutable_data.get('full_name'):
                mutable_data['candidate_name'] = mutable_data['full_name']

        # Support 'result' or 'placement' alias for 'result_placement'
        if not mutable_data.get('result_placement'):
            if mutable_data.get('result'):
                mutable_data['result_placement'] = mutable_data['result']
            elif mutable_data.get('placement'):
                mutable_data['result_placement'] = mutable_data['placement']

        # Support 'review' or 'content' alias for 'quote'
        if not mutable_data.get('quote'):
            if mutable_data.get('review'):
                mutable_data['quote'] = mutable_data['review']
            elif mutable_data.get('content'):
                mutable_data['quote'] = mutable_data['content']

        # Support 'image' or 'avatar' alias for 'photo'
        if not mutable_data.get('photo'):
            if mutable_data.get('image'):
                mutable_data['photo'] = mutable_data['image']
            elif mutable_data.get('avatar'):
                mutable_data['photo'] = mutable_data['avatar']

        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        if not attrs.get('candidate_name') and not (self.instance and self.instance.candidate_name):
            raise serializers.ValidationError({'candidate_name': 'Candidate full name is required.'})
        if not attrs.get('quote') and not (self.instance and self.instance.quote):
            raise serializers.ValidationError({'quote': 'Candidate quote / review is required.'})
        return attrs
