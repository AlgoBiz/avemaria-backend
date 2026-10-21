from django.db import models
from django.utils.text import slugify
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.categories.models import Category

class CategoryCreateSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    title = serializers.CharField(required=False)

    class Meta:
        model = Category
        fields = (
            'id', 'title', 'slug', 'cover_image',
            'description', 'created_at'
        )
        extra_kwargs = {
            'cover_image': {'required': False, 'allow_null': True},
            'description': {'required': False, 'allow_blank': True}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        if hasattr(instance, 'slug'):
            ret['slug'] = instance.slug
        return ret

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = data.copy()

        # Field alias: Category Title
        if not data.get('title'):
            for alias in ['category_title', 'name', 'category_name', 'category']:
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

    def validate(self, attrs):
        title = attrs.get('title') or (self.instance and self.instance.title)
        if not title or not str(title).strip():
            raise serializers.ValidationError({"title": "Category title is required."})

        cleaned = ' '.join(str(title).strip().split())
        attrs['title'] = cleaned

        cat_slug = slugify(cleaned)
        existing_qs = Category.objects.filter(
            models.Q(title__iexact=cleaned) | models.Q(slug=cat_slug)
        )
        if self.instance:
            existing_qs = existing_qs.exclude(pk=self.instance.pk)

        existing = existing_qs.first()
        if existing:
            if not self.instance and existing.is_deleted:
                # Soft-deleted record will be restored in create()
                pass
            else:
                raise serializers.ValidationError({"title": f"Course category '{cleaned}' already exists."})
        return attrs

    def create(self, validated_data):
        title = validated_data.get('title')
        cat_slug = slugify(title)
        existing = Category.objects.filter(
            models.Q(title__iexact=title) | models.Q(slug=cat_slug)
        ).first()
        if existing:
            if existing.is_deleted:
                existing.is_deleted = False
                for k, v in validated_data.items():
                    setattr(existing, k, v)
                existing.save()
                return existing
            raise serializers.ValidationError({"title": f"Course category '{title}' already exists."})
        return super().create(validated_data)


class CategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    title = serializers.CharField(required=False)
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        if hasattr(instance, 'slug'):
            ret['slug'] = instance.slug
        if hasattr(instance, 'title'):
            ret['name'] = instance.title
        return ret

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = data.copy()

        # Field alias: Category Title
        if not data.get('title'):
            for alias in ['category_title', 'name', 'category_name', 'category']:
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

    def validate(self, attrs):
        title = attrs.get('title') or (self.instance and self.instance.title)
        if not title or not str(title).strip():
            raise serializers.ValidationError({"title": "Category title is required."})

        cleaned = ' '.join(str(title).strip().split())
        attrs['title'] = cleaned

        cat_slug = slugify(cleaned)
        existing_qs = Category.objects.filter(
            models.Q(title__iexact=cleaned) | models.Q(slug=cat_slug)
        )
        if self.instance:
            existing_qs = existing_qs.exclude(pk=self.instance.pk)

        existing = existing_qs.first()
        if existing:
            if not self.instance and existing.is_deleted:
                # Soft-deleted record will be restored in create()
                pass
            else:
                raise serializers.ValidationError({"title": f"Course category '{cleaned}' already exists."})
        return attrs

    def create(self, validated_data):
        title = validated_data.get('title')
        cat_slug = slugify(title)
        existing = Category.objects.filter(
            models.Q(title__iexact=title) | models.Q(slug=cat_slug)
        ).first()
        if existing:
            if existing.is_deleted:
                existing.is_deleted = False
                for k, v in validated_data.items():
                    setattr(existing, k, v)
                existing.save()
                return existing
            raise serializers.ValidationError({"title": f"Course category '{title}' already exists."})
        return super().create(validated_data)

    @extend_schema_field(serializers.CharField())
    def get_programmes_label(self, obj):
        count = obj.programmes_count
        return f"{count} {'Programme' if count == 1 else 'Programmes'}"


class CategoryListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    cover_image = serializers.SerializerMethodField()
    programmes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'title', 'cover_image', 'description', 'programmes_count')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        return ret

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cover_image(self, obj):
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None


