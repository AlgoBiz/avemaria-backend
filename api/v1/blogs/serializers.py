from rest_framework import serializers
from apps.blogs.models import Blog, BlogCategory

class BlogCategorySerializer(serializers.ModelSerializer):
    articles_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = BlogCategory
        fields = ('id', 'name', 'slug', 'description', 'articles_count', 'is_active', 'is_deleted', 'created_at', 'updated_at')
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False}
        }

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = data.copy()
        if not data.get('name'):
            for alias in ['title', 'category_name', 'category']:
                if data.get(alias):
                    data['name'] = data[alias]
                    break
        return super().to_internal_value(data)

class BlogListSerializer(serializers.ModelSerializer):
    content_blocks_count = serializers.IntegerField(read_only=True)
    publish_date_formatted = serializers.CharField(read_only=True)

    class Meta:
        model = Blog
        fields = (
            'id', 'title', 'slug', 'sub_heading', 'category',
            'read_time', 'publish_date', 'publish_date_formatted',
            'author_name', 'cover_image',
            'content_blocks_count', 'is_published', 'is_active', 'is_deleted',
            'created_at'
        )

class BlogDetailSerializer(serializers.ModelSerializer):
    content_blocks_count = serializers.IntegerField(read_only=True)
    publish_date_formatted = serializers.CharField(read_only=True)
    content_blocks = serializers.JSONField(required=False, default=list)
    meta_keywords = serializers.JSONField(required=False, default=list)

    class Meta:
        model = Blog
        fields = (
            'id', 'title', 'slug', 'sub_heading', 'category',
            'read_time', 'publish_date', 'publish_date_formatted',
            'author_name', 'cover_image',
            'content_blocks', 'content_blocks_count',
            'meta_description', 'meta_keywords',
            'is_published', 'is_active', 'is_deleted',
            'created_at', 'updated_at'
        )
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'is_published': {'default': True, 'required': False}
        }

