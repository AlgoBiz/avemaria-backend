from rest_framework import serializers
from apps.gallery.models import GalleryItem

class GalleryItemSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='caption', required=False)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = GalleryItem
        fields = (
            'id', 'caption', 'title', 'category', 'image', 'image_url',
            'alt_text', 'order', 'is_active', 'is_deleted', 'created_at', 'updated_at'
        )
        extra_kwargs = {
            'caption': {'required': False},
            'image': {'required': False},
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False}
        }

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def to_internal_value(self, data):
        # Handle QueryDict (multipart) and regular dictionary
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        # Support 'title' alias for 'caption'
        if not mutable_data.get('caption') and mutable_data.get('title'):
            mutable_data['caption'] = mutable_data['title']

        # Support 'photo' or 'file' alias for 'image'
        if not mutable_data.get('image'):
            if mutable_data.get('photo'):
                mutable_data['image'] = mutable_data['photo']
            elif mutable_data.get('file'):
                mutable_data['image'] = mutable_data['file']

        # Support 'description' alias for 'alt_text'
        if not mutable_data.get('alt_text') and mutable_data.get('description'):
            mutable_data['alt_text'] = mutable_data['description']

        # Normalize category choice case-insensitively if needed
        cat = mutable_data.get('category')
        if cat and isinstance(cat, str):
            for choice_val, choice_label in GalleryItem.CATEGORY_CHOICES:
                if cat.strip().lower() == choice_val.lower():
                    mutable_data['category'] = choice_val
                    break

        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        if not attrs.get('caption') and not (self.instance and self.instance.caption):
            raise serializers.ValidationError({'caption': 'Photo caption or title is required.'})
        if self.instance is None and not attrs.get('image'):
            raise serializers.ValidationError({'image': 'Image file is required.'})
        return attrs
