import json
import datetime
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.blogs.models import Blog, BlogCategory


class BlogCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='name', required=False)
    articles_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = BlogCategory
        fields = (
            'id', 'name', 'category_name', 'slug', 'description',
            'articles_count', 'is_active', 'is_deleted', 'created_at', 'updated_at'
        )
        extra_kwargs = {
            'name': {'required': False},
            'slug': {'read_only': True},
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False}
        }

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        if not mutable_data.get('name'):
            for alias in ['category_name', 'title', 'category']:
                if mutable_data.get(alias):
                    mutable_data['name'] = mutable_data[alias]
                    break
        return super().to_internal_value(mutable_data)

    def validate_name(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Category name is required.")
        return value.strip()


class BlogListSerializer(serializers.ModelSerializer):
    heading = serializers.CharField(source='title', read_only=True)
    excerpt = serializers.CharField(source='sub_heading', read_only=True)
    content_blocks_count = serializers.IntegerField(read_only=True)
    blocks_count = serializers.IntegerField(source='content_blocks_count', read_only=True)
    publish_date_formatted = serializers.CharField(read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = (
            'id', 'title', 'heading', 'slug', 'sub_heading', 'excerpt', 'category',
            'read_time', 'publish_date', 'publish_date_formatted',
            'author_name', 'cover_image', 'cover_image_url',
            'content_blocks_count', 'blocks_count',
            'is_published', 'is_active', 'is_deleted',
            'created_at'
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cover_image_url(self, obj):
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None


class BlogDetailSerializer(serializers.ModelSerializer):
    heading = serializers.CharField(source='title', required=False)
    excerpt = serializers.CharField(source='sub_heading', required=False)
    category = serializers.CharField(required=True, allow_blank=False)
    content_blocks_count = serializers.IntegerField(read_only=True)
    blocks_count = serializers.IntegerField(source='content_blocks_count', read_only=True)
    publish_date_formatted = serializers.CharField(read_only=True)
    content_blocks = serializers.JSONField(required=False, default=list)
    meta_keywords = serializers.JSONField(required=False, default=list)
    meta_tags = serializers.JSONField(source='meta_keywords', required=False, read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = (
            'id', 'title', 'heading', 'slug', 'sub_heading', 'excerpt', 'category',
            'read_time', 'publish_date', 'publish_date_formatted',
            'author_name', 'cover_image', 'cover_image_url',
            'content_blocks', 'content_blocks_count', 'blocks_count',
            'meta_description', 'meta_keywords', 'meta_tags',
            'is_published', 'is_active', 'is_deleted',
            'created_at', 'updated_at'
        )
        extra_kwargs = {
            'title': {'required': False},
            'sub_heading': {'required': False},
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'is_published': {'default': True, 'required': False}
        }

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cover_image_url(self, obj):
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        # Title / Heading alias
        if not mutable_data.get('title'):
            for alias in ['heading', 'article_title', 'name']:
                if mutable_data.get(alias):
                    mutable_data['title'] = mutable_data[alias]
                    break

        # Sub Heading / Excerpt / Overview alias
        if not mutable_data.get('sub_heading'):
            for alias in ['excerpt', 'overview', 'summary', 'sub_title', 'subheading']:
                if mutable_data.get(alias):
                    mutable_data['sub_heading'] = mutable_data[alias]
                    break

        # Category alias & auto-creation
        if not mutable_data.get('category'):
            for alias in ['category_name', 'topic', 'blog_category']:
                if mutable_data.get(alias):
                    mutable_data['category'] = mutable_data[alias]
                    break

        cat_val = mutable_data.get('category')
        if cat_val is not None and str(cat_val).strip():
            if isinstance(cat_val, dict):
                cat_val = cat_val.get('name') or cat_val.get('title') or cat_val.get('id')
            cleaned_val = str(cat_val).strip()
            from apps.blogs.models import BlogCategory
            from django.utils.text import slugify
            from django.db.models import Q
            if cleaned_val.isdigit():
                found_cat = BlogCategory.objects.filter(id=int(cleaned_val), is_deleted=False).first()
            else:
                found_cat = BlogCategory.objects.filter(
                    is_deleted=False
                ).filter(
                    Q(name__iexact=cleaned_val) | Q(slug__iexact=slugify(cleaned_val))
                ).first()
            if not found_cat:
                raise serializers.ValidationError({
                    'category': f"Blog category '{cleaned_val}' does not exist. Please add the category first using the blog categories API."
                })
            mutable_data['category'] = found_cat.name
        elif not getattr(self, 'partial', False):
            raise serializers.ValidationError({
                'category': "Blog category is required. Please select an existing category or add it first."
            })

        # Author Name alias
        if not mutable_data.get('author_name'):
            for alias in ['author', 'authorName', 'written_by']:
                if mutable_data.get(alias):
                    mutable_data['author_name'] = mutable_data[alias]
                    break

        # Cover image alias
        if not mutable_data.get('cover_image'):
            for alias in ['image', 'photo', 'file', 'cover']:
                if mutable_data.get(alias):
                    mutable_data['cover_image'] = mutable_data[alias]
                    break

        # Meta tags alias
        if not mutable_data.get('meta_keywords'):
            for alias in ['meta_tags', 'tags', 'keywords']:
                if mutable_data.get(alias):
                    mutable_data['meta_keywords'] = mutable_data[alias]
                    break

        # Parse stringified meta_keywords
        keywords = mutable_data.get('meta_keywords')
        if isinstance(keywords, str):
            try:
                mutable_data['meta_keywords'] = json.loads(keywords)
            except Exception:
                mutable_data['meta_keywords'] = [k.strip() for k in keywords.split(',') if k.strip()]

        # Parse stringified content_blocks
        blocks = mutable_data.get('content_blocks')
        if isinstance(blocks, str):
            try:
                mutable_data['content_blocks'] = json.loads(blocks)
            except Exception:
                mutable_data['content_blocks'] = []

        # Parse publish_date (e.g. "11 September 2026", "2026-09-11")
        pdate = mutable_data.get('publish_date')
        if pdate and isinstance(pdate, str):
            for fmt in ('%Y-%m-%d', '%d %B %Y', '%d %b %Y', '%B %d, %Y', '%d/%m/%Y'):
                try:
                    dt = datetime.datetime.strptime(pdate.strip(), fmt)
                    mutable_data['publish_date'] = dt.date().isoformat()
                    break
                except ValueError:
                    continue

        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        if not attrs.get('title') and not (self.instance and self.instance.title):
            raise serializers.ValidationError({'title': 'Heading (Article Title) is required.'})
        if not attrs.get('sub_heading') and not (self.instance and self.instance.sub_heading):
            raise serializers.ValidationError({'sub_heading': 'Sub Heading (Overview / Excerpt) is required.'})
        if not attrs.get('category') and not (self.instance and self.instance.category):
            raise serializers.ValidationError({'category': 'Blog category is required. A category must be created or selected before adding a blog article.'})
        return attrs


class BlogStatsSerializer(serializers.Serializer):
    total_categories = serializers.IntegerField()
    total_articles = serializers.IntegerField()
    summary_display = serializers.CharField()


class BlogCategoriesResponseSerializer(serializers.Serializer):
    total_all = serializers.IntegerField()
    categories = serializers.ListField(child=serializers.CharField())
    results = BlogCategorySerializer(many=True)


class BlogTogglePublishedResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    is_published = serializers.BooleanField()
    message = serializers.CharField()
