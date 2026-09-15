from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.gallery.models import GalleryItem, GalleryCategory


class GalleryCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='name', required=False)
    photos_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = GalleryCategory
        fields = (
            'id', 'name', 'category_name', 'description',
            'photos_count', 'is_active', 'created_at', 'updated_at'
        )
        extra_kwargs = {
            'name': {'required': False},
        }

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        # Support "category_name" alias from UI modal
        if not mutable_data.get('name') and mutable_data.get('category_name'):
            mutable_data['name'] = mutable_data['category_name']

        return super().to_internal_value(mutable_data)

    def validate_name(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Category name is required.")
        return value.strip()


class GalleryItemSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False, allow_blank=True)
    caption = serializers.CharField(required=False, allow_blank=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = GalleryItem
        fields = (
            'id', 'title', 'caption', 'category', 'category_slug',
            'image', 'image_url', 'alt_text', 'order',
            'is_active', 'is_deleted', 'created_at', 'updated_at'
        )
        extra_kwargs = {
            'image': {'required': False},
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False}
        }

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        # Support "title" and "caption" interoperability
        title = mutable_data.get('title')
        caption = mutable_data.get('caption')
        if not caption and title:
            mutable_data['caption'] = title
        elif not title and caption:
            mutable_data['title'] = caption

        # Support "default_category" / "category_name" for category
        if not mutable_data.get('category'):
            if mutable_data.get('default_category'):
                mutable_data['category'] = mutable_data['default_category']
            elif mutable_data.get('category_name'):
                mutable_data['category'] = mutable_data['category_name']

        cat_val = mutable_data.get('category')
        if cat_val is not None and str(cat_val).strip():
            if isinstance(cat_val, dict):
                cat_val = cat_val.get('name') or cat_val.get('title') or cat_val.get('id')
            cleaned_val = str(cat_val).strip()
            from apps.gallery.models import GalleryCategory
            from django.utils.text import slugify
            from django.db.models import Q
            if cleaned_val.isdigit():
                found_cat = GalleryCategory.objects.filter(id=int(cleaned_val), is_deleted=False).first()
            else:
                found_cat = GalleryCategory.objects.filter(
                    is_deleted=False
                ).filter(
                    Q(name__iexact=cleaned_val) | Q(slug__iexact=slugify(cleaned_val))
                ).first()
            if not found_cat:
                raise serializers.ValidationError({
                    'category': f"Gallery category '{cleaned_val}' does not exist. Please add the category first using the gallery categories API."
                })
            mutable_data['category'] = found_cat.name
            mutable_data['category_slug'] = found_cat.slug
        elif not getattr(self, 'partial', False):
            raise serializers.ValidationError({
                'category': "Gallery category is required. Please select an existing category or add it first."
            })

        # Support "photo" or "file" alias for "image"
        if not mutable_data.get('image'):
            if mutable_data.get('photo'):
                mutable_data['image'] = mutable_data['photo']
            elif mutable_data.get('file'):
                mutable_data['image'] = mutable_data['file']

        # Support "description" alias for "alt_text"
        if not mutable_data.get('alt_text') and mutable_data.get('description'):
            mutable_data['alt_text'] = mutable_data['description']

        return super().to_internal_value(mutable_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Ensure title and caption are both populated for the frontend card
        if not ret.get('title') and ret.get('caption'):
            ret['title'] = ret['caption']
        if not ret.get('caption') and ret.get('title'):
            ret['caption'] = ret['title']
        return ret
