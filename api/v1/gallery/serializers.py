from django.db import models
from django.utils.text import slugify
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.gallery.models import GalleryItem, GalleryCategory


class GalleryCategoryCreateSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    name = serializers.CharField(required=False)

    class Meta:
        model = GalleryCategory
        fields = ('id', 'slug', 'name', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'slug', 'created_at', 'updated_at')

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        # Support "category" or "category_name" or "title" alias
        if not mutable_data.get('name'):
            for alias in ['category', 'category_name', 'title', 'category_title']:
                if mutable_data.get(alias):
                    mutable_data['name'] = mutable_data[alias]
                    break

        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        name = attrs.get('name') or (self.instance and self.instance.name)
        if not name or not str(name).strip():
            raise serializers.ValidationError({"name": "Category name is required."})

        cleaned = ' '.join(str(name).strip().split())
        attrs['name'] = cleaned

        cat_slug = slugify(cleaned)
        existing_qs = GalleryCategory.objects.filter(
            models.Q(name__iexact=cleaned) | models.Q(slug=cat_slug)
        )
        if self.instance:
            existing_qs = existing_qs.exclude(pk=self.instance.pk)

        existing = existing_qs.first()
        if existing:
            if not self.instance and existing.is_deleted:
                # Soft-deleted record will be restored in create()
                pass
            else:
                raise serializers.ValidationError({"name": f"Gallery category '{cleaned}' already exists."})
        return attrs

    def create(self, validated_data):
        name = validated_data.get('name')
        cat_slug = slugify(name)
        existing = GalleryCategory.objects.filter(
            models.Q(name__iexact=name) | models.Q(slug=cat_slug)
        ).first()
        if existing:
            if existing.is_deleted:
                existing.is_deleted = False
                for k, v in validated_data.items():
                    setattr(existing, k, v)
                existing.save()
                return existing
            raise serializers.ValidationError({"name": f"Gallery category '{name}' already exists."})
        return super().create(validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = str(instance.uuid)
        ret['slug'] = instance.slug
        ret['name'] = instance.name
        return ret


class GalleryCategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    category = serializers.CharField(source='name', required=False)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    image = serializers.ImageField(required=False, allow_null=True)
    alt_text = serializers.CharField(required=False, allow_blank=True, default='')
    photos_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = GalleryCategory
        fields = (
            'id', 'slug', 'name', 'category', 'description',
            'image', 'alt_text', 'photos_count',
            'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'slug', 'created_at', 'updated_at')
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
            'alt_text': {'required': False, 'allow_blank': True},
            'image': {'required': False, 'allow_null': True},
        }

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        # Support "category" or "category_name" or "title" alias
        if not mutable_data.get('name'):
            for alias in ['category', 'category_name', 'title', 'category_title']:
                if mutable_data.get(alias):
                    mutable_data['name'] = mutable_data[alias]
                    break

        if not mutable_data.get('category') and mutable_data.get('name'):
            mutable_data['category'] = mutable_data['name']

        # Support "photo" or "file" alias for "image"
        if not mutable_data.get('image'):
            if mutable_data.get('photo'):
                mutable_data['image'] = mutable_data['photo']
            elif mutable_data.get('file'):
                mutable_data['image'] = mutable_data['file']

        if mutable_data.get('image') in ['', 'null', 'None', None]:
            mutable_data.pop('image', None)

        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        name = attrs.get('name') or (self.instance and self.instance.name)
        if not name or not str(name).strip():
            raise serializers.ValidationError({"name": "Category name is required."})

        cleaned = ' '.join(str(name).strip().split())
        attrs['name'] = cleaned

        cat_slug = slugify(cleaned)
        existing_qs = GalleryCategory.objects.filter(
            models.Q(name__iexact=cleaned) | models.Q(slug=cat_slug)
        )
        if self.instance:
            existing_qs = existing_qs.exclude(pk=self.instance.pk)

        existing = existing_qs.first()
        if existing:
            if not self.instance and existing.is_deleted:
                # Soft-deleted record will be restored in create()
                pass
            else:
                raise serializers.ValidationError({"name": f"Gallery category '{cleaned}' already exists."})
        return attrs

    def create(self, validated_data):
        name = validated_data.get('name')
        cat_slug = slugify(name)
        existing = GalleryCategory.objects.filter(
            models.Q(name__iexact=name) | models.Q(slug=cat_slug)
        ).first()
        if existing:
            if existing.is_deleted:
                existing.is_deleted = False
                for k, v in validated_data.items():
                    setattr(existing, k, v)
                existing.save()
                return existing
            raise serializers.ValidationError({"name": f"Gallery category '{name}' already exists."})
        return super().create(validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = str(instance.uuid)
        ret['slug'] = instance.slug
        ret['name'] = instance.name
        ret['category'] = instance.name

        request = self.context.get('request')
        image_url = None
        alt_text = instance.alt_text or ''

        # 1. Use category's own uploaded image if available
        if instance.image:
            image_url = request.build_absolute_uri(instance.image.url) if request else instance.image.url
        else:
            # 2. Fallback to latest photo in this category
            from apps.gallery.models import GalleryItem
            from django.db.models import Q
            latest_item = GalleryItem.objects.filter(
                Q(category__iexact=instance.name) | Q(category_slug__iexact=instance.slug),
                is_deleted=False
            ).order_by('-created_at', '-id').first()
            if latest_item:
                if latest_item.image:
                    image_url = request.build_absolute_uri(latest_item.image.url) if request else latest_item.image.url
                if not alt_text:
                    alt_text = latest_item.alt_text or latest_item.title or latest_item.caption or ''

        ret['image'] = image_url
        ret['alt_text'] = alt_text
        return ret


GalleryCategoryListSerializer = GalleryCategorySerializer


class GalleryCategoryMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer returning only id, name, title, and slug."""
    id = serializers.CharField(source='uuid_str', read_only=True)
    name = serializers.CharField(read_only=True)
    title = serializers.CharField(source='name', read_only=True)
    slug = serializers.CharField(read_only=True)

    class Meta:
        model = GalleryCategory
        fields = ('id', 'name', 'title', 'slug')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        return ret


class GalleryItemSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    title = serializers.CharField(required=False, allow_blank=True, write_only=True)
    caption = serializers.CharField(required=False, allow_blank=True, write_only=True)
    order = serializers.IntegerField(required=False, default=0, write_only=True)
    category_slug = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = GalleryItem
        fields = (
            'id', 'slug', 'category', 'image', 'alt_text',
            'is_active', 'is_deleted', 'created_at', 'updated_at',
            'title', 'caption', 'order', 'category_slug'
        )
        read_only_fields = ('id', 'slug', 'created_at', 'updated_at')
        extra_kwargs = {
            'image': {'required': False},
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'title': {'write_only': True},
            'caption': {'write_only': True},
            'order': {'write_only': True},
            'category_slug': {'write_only': True},
        }

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

        # Support "description" alias for "alt_text"
        if not mutable_data.get('alt_text') and mutable_data.get('description'):
            mutable_data['alt_text'] = mutable_data['description']

        if not mutable_data.get('title') and not mutable_data.get('caption') and mutable_data.get('alt_text'):
            mutable_data['title'] = mutable_data['alt_text']
            mutable_data['caption'] = mutable_data['alt_text']

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

        return super().to_internal_value(mutable_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = str(instance.uuid)
        ret['slug'] = instance.slug
        # Exclude unwanted fields from response
        for field in ('title', 'caption', 'category_slug', 'image_url', 'order'):
            ret.pop(field, None)
        return ret
