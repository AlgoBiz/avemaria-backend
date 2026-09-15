from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.categories.models import Category

class CategorySerializer(serializers.ModelSerializer):
    programmes_count = serializers.IntegerField(read_only=True)
    programmes_label = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            'id', 'title', 'slug', 'cover_image',
            'description', 'programmes_count', 'programmes_label', 'order',
            'is_active', 'is_deleted', 'created_at', 'updated_at'
        )
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'cover_image': {'required': False, 'allow_null': True},
            'description': {'required': False, 'allow_blank': True}
        }

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = data.copy()

        # Field alias: Category Title
        if not data.get('title'):
            for alias in ['category_title', 'name', 'category_name']:
                if data.get(alias):
                    data['title'] = data[alias]
                    break

        # Field alias: Cover image
        if not data.get('cover_image'):
            for alias in ['image', 'cover', 'file', 'category_cover']:
                if data.get(alias):
                    data['cover_image'] = data[alias]
                    break

        # Field alias: Description
        if not data.get('description'):
            for alias in ['category_description', 'desc', 'bio']:
                if data.get(alias):
                    data['description'] = data[alias]
                    break

        # Handle empty string for file/image
        if data.get('cover_image') == '' or data.get('cover_image') == 'null':
            data.pop('cover_image', None)

        return super().to_internal_value(data)

    @extend_schema_field(serializers.CharField())
    def get_programmes_label(self, obj):
        count = obj.programmes_count
        return f"{count} {'Programme' if count == 1 else 'Programmes'}"


class CategoryListSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()
    programmes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ('title', 'cover_image', 'description', 'programmes_count')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cover_image(self, obj):
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None

