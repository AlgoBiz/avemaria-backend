from collections import OrderedDict
from django.db import models
from django.utils.text import slugify
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.resources.models import PaidResource, ResourcePDF, ResourceCategory

class ResourceCategoryCreateSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    name = serializers.CharField(required=False)

    class Meta:
        model = ResourceCategory
        fields = ('id', 'name', 'slug', 'created_at', 'updated_at')

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
        if not data.get('name'):
            for alias in ['title', 'category_name', 'category', 'category_title']:
                if data.get(alias):
                    data['name'] = data[alias]
                    break
        return super().to_internal_value(data)

    def validate(self, attrs):
        name = attrs.get('name') or (self.instance and self.instance.name)
        if not name or not str(name).strip():
            raise serializers.ValidationError({"name": "Category name is required."})

        cleaned = ' '.join(str(name).strip().split())
        attrs['name'] = cleaned

        cat_slug = slugify(cleaned)
        existing_qs = ResourceCategory.objects.filter(
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
                raise serializers.ValidationError({"name": f"Resource category '{cleaned}' already exists."})
        return attrs

    def create(self, validated_data):
        name = validated_data.get('name')
        cat_slug = slugify(name)
        existing = ResourceCategory.objects.filter(
            models.Q(name__iexact=name) | models.Q(slug=cat_slug)
        ).first()
        if existing:
            if existing.is_deleted:
                existing.is_deleted = False
                for k, v in validated_data.items():
                    setattr(existing, k, v)
                existing.save()
                return existing
            raise serializers.ValidationError({"name": f"Resource category '{name}' already exists."})
        return super().create(validated_data)


class ResourceCategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    name = serializers.CharField(required=False)
    resources_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ResourceCategory
        fields = ('id', 'name', 'slug', 'resources_count', 'is_active', 'is_deleted', 'created_at', 'updated_at')
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        if hasattr(instance, 'slug'):
            ret['slug'] = instance.slug
        if hasattr(instance, 'name'):
            ret['title'] = instance.name
            ret['category'] = instance.name
        return ret

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = data.copy()
        if not data.get('name'):
            for alias in ['title', 'category_name', 'category', 'category_title']:
                if data.get(alias):
                    data['name'] = data[alias]
                    break
        return super().to_internal_value(data)

    def validate(self, attrs):
        name = attrs.get('name') or (self.instance and self.instance.name)
        if not name or not str(name).strip():
            raise serializers.ValidationError({"name": "Category name is required."})

        cleaned = ' '.join(str(name).strip().split())
        attrs['name'] = cleaned

        cat_slug = slugify(cleaned)
        existing_qs = ResourceCategory.objects.filter(
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
                raise serializers.ValidationError({"name": f"Resource category '{cleaned}' already exists."})
        return attrs

    def create(self, validated_data):
        name = validated_data.get('name')
        cat_slug = slugify(name)
        existing = ResourceCategory.objects.filter(
            models.Q(name__iexact=name) | models.Q(slug=cat_slug)
        ).first()
        if existing:
            if existing.is_deleted:
                existing.is_deleted = False
                for k, v in validated_data.items():
                    setattr(existing, k, v)
                existing.save()
                return existing
            raise serializers.ValidationError({"name": f"Resource category '{name}' already exists."})
        return super().create(validated_data)


class ResourceCategoryMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer returning only id, name, title, and slug."""
    id = serializers.CharField(source='uuid_str', read_only=True)
    name = serializers.CharField(read_only=True)
    title = serializers.CharField(source='name', read_only=True)
    slug = serializers.CharField(read_only=True)

    class Meta:
        model = ResourceCategory
        fields = ('id', 'name', 'title', 'slug')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        return ret


class ResourcePDFSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    uploaded_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = ResourcePDF
        fields = ('id', 'title', 'file', 'file_size', 'uploaded_at', 'created_at')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        ret['title'] = getattr(instance, 'title', None) or (instance.file.name.split('/')[-1] if getattr(instance, 'file', None) else '')
        return ret


class ResourceListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    resource_type = serializers.CharField(read_only=True)
    price = serializers.CharField(read_only=True)
    pdf_count = serializers.IntegerField(read_only=True)
    highlights = serializers.JSONField(read_only=True)

    class Meta:
        model = PaidResource
        fields = (
            'id',
            'slug',
            'title',
            'resource_type',
            'category',
            'price',
            'description',
            'highlights',
            'pdf_count',
        )

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ordered_ret = OrderedDict()
        for field in self.Meta.fields:
            if field in ret:
                ordered_ret[field] = ret[field]
        for k, v in ret.items():
            if k not in ordered_ret:
                ordered_ret[k] = v
        if hasattr(instance, 'uuid'):
            ordered_ret['id'] = str(instance.uuid)
        if hasattr(instance, 'slug'):
            ordered_ret['slug'] = instance.slug

        rt = getattr(instance, 'resource_type', None) or 'note'
        ordered_ret['resource_type'] = rt
        ordered_ret['resource_type_display'] = 'Question Paper' if rt == 'question paper' else 'Notes'

        curr = getattr(instance, 'currency', None) or '£'
        if instance.price is None or instance.price <= 0:
            ordered_ret['price'] = 'free'
            ordered_ret['price_formatted'] = 'Free'
            ordered_ret['is_free'] = True
            ordered_ret['is_paid'] = False
        else:
            ordered_ret['price'] = f"{instance.price:.2f}"
            ordered_ret['price_formatted'] = f"{curr}{instance.price:.2f}"
            ordered_ret['is_free'] = False
            ordered_ret['is_paid'] = True

        return ordered_ret


class PaidResourceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    slug = serializers.CharField(read_only=True)
    pdf_files = ResourcePDFSerializer(many=True, read_only=True)
    pdf_count = serializers.IntegerField(read_only=True)
    category = serializers.CharField(required=True, allow_blank=False)
    resource_type = serializers.CharField(required=False, default='note')
    price = serializers.CharField(required=False, allow_blank=True, default='free')
    highlights = serializers.JSONField(required=False, default=list)

    class Meta:
        model = PaidResource
        fields = (
            'id',
            'slug',
            'title',
            'resource_type',
            'category',
            'course_name',
            'price',
            'description',
            'highlights',
            'pdf_count',
            'pdf_files',
            'is_active',
            'is_deleted',
            'created_at',
            'updated_at'
        )
        extra_kwargs = {
            'course_name': {'required': False, 'allow_blank': True},
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'description': {'required': False, 'allow_blank': True}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ordered_ret = OrderedDict()
        for field in self.Meta.fields:
            if field in ret:
                ordered_ret[field] = ret[field]
        for k, v in ret.items():
            if k not in ordered_ret:
                ordered_ret[k] = v
        if hasattr(instance, 'uuid'):
            ordered_ret['id'] = str(instance.uuid)
        if hasattr(instance, 'slug'):
            ordered_ret['slug'] = instance.slug
        ordered_ret['course_name'] = instance.course_name

        rt = getattr(instance, 'resource_type', None) or 'note'
        ordered_ret['resource_type'] = rt
        ordered_ret['resource_type_display'] = 'Question Paper' if rt == 'question paper' else 'Notes'

        curr = getattr(instance, 'currency', None) or '£'
        if instance.price is None or instance.price <= 0:
            ordered_ret['price'] = 'free'
            ordered_ret['price_formatted'] = 'Free'
            ordered_ret['is_free'] = True
            ordered_ret['is_paid'] = False
        else:
            ordered_ret['price'] = f"{instance.price:.2f}"
            ordered_ret['price_formatted'] = f"{curr}{instance.price:.2f}"
            ordered_ret['is_free'] = False
            ordered_ret['is_paid'] = True

        pdf_cnt = instance.pdf_count
        ordered_ret['pdf_count_display'] = f"{pdf_cnt} {'PDF attached' if pdf_cnt == 1 else 'PDFs attached'}"
        return ordered_ret

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        elif hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        # Support 'course', 'programme_name', 'programme' alias for 'course_name'
        if not mutable_data.get('course_name'):
            for alias in ['course', 'programme_name', 'programme', 'course_title']:
                if mutable_data.get(alias):
                    mutable_data['course_name'] = str(mutable_data[alias])
                    break

        # Support 'summary' alias for 'description'
        if not mutable_data.get('description') and mutable_data.get('summary'):
            mutable_data['description'] = mutable_data['summary']

        # Category alias & auto-creation
        if not mutable_data.get('category'):
            for alias in ['category_name', 'resource_category', 'category_title']:
                if mutable_data.get(alias):
                    mutable_data['category'] = str(mutable_data[alias])
                    break

        cat_val = mutable_data.get('category')
        if cat_val is not None and str(cat_val).strip():
            if isinstance(cat_val, dict):
                cat_val = cat_val.get('name') or cat_val.get('title') or cat_val.get('id')
            cleaned_val = str(cat_val).strip()
            from apps.resources.models import ResourceCategory
            from django.utils.text import slugify
            from django.db.models import Q
            if cleaned_val.isdigit():
                found_cat = ResourceCategory.objects.filter(id=int(cleaned_val), is_deleted=False).first()
            else:
                found_cat = ResourceCategory.objects.filter(
                    is_deleted=False
                ).filter(
                    Q(name__iexact=cleaned_val) | Q(slug__iexact=slugify(cleaned_val))
                ).first()
            if not found_cat:
                raise serializers.ValidationError({
                    'category': f"Resource category '{cleaned_val}' does not exist. Please add the category first using the resource categories API."
                })
            mutable_data['category'] = found_cat.name
        elif not getattr(self, 'partial', False):
            raise serializers.ValidationError({
                'category': "Resource category is required. Please select an existing category or add it first."
            })

        # Resource Type handling & normalization
        raw_rt = mutable_data.get('resource_type')
        if raw_rt is None:
            for alias in ['resourceType', 'resourcetype', 'material_type', 'item_type']:
                if mutable_data.get(alias) is not None:
                    raw_rt = mutable_data[alias]
                    break

        if raw_rt is not None and str(raw_rt).strip():
            cleaned_rt = str(raw_rt).strip().lower()
            if cleaned_rt in ['notes', 'note', 'study note', 'study notes', 'study_note', 'study_notes']:
                mutable_data['resource_type'] = 'note'
            elif cleaned_rt in ['question paper', 'question_paper', 'question-paper', 'question papers', 'question', 'question_papers']:
                mutable_data['resource_type'] = 'question paper'
            else:
                mutable_data['resource_type'] = cleaned_rt
        elif not getattr(self, 'partial', False):
            mutable_data['resource_type'] = 'note'

        # Clean up price (e.g. 'free', 0, '0', '', None, '£29.00', 29.00, '$29.00')
        if 'price' in mutable_data or not getattr(self, 'partial', False):
            price_val = mutable_data.get('price')
            if price_val is None or str(price_val).strip() == '':
                mutable_data['price'] = '0.00'
            elif isinstance(price_val, (int, float)):
                if price_val <= 0:
                    mutable_data['price'] = '0.00'
                else:
                    mutable_data['price'] = f"{price_val:.2f}"
            elif isinstance(price_val, str):
                cleaned_price = price_val.strip()
                if cleaned_price.lower() in ['free', 'free of cost', 'nil', '', '0', '0.0', '0.00', 'none', 'null']:
                    mutable_data['price'] = '0.00'
                else:
                    cleaned_price = cleaned_price.replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                    try:
                        f_val = float(cleaned_price)
                        if f_val <= 0:
                            mutable_data['price'] = '0.00'
                        else:
                            mutable_data['price'] = f"{f_val:.2f}"
                    except ValueError:
                        mutable_data['price'] = cleaned_price

        # Also support is_paid / paid boolean flags from UI switches (see Image 1 & 2)
        if 'is_paid' in mutable_data and (mutable_data['is_paid'] is False or str(mutable_data['is_paid']).lower() in ['false', '0']):
            mutable_data['price'] = '0.00'
        elif 'paid' in mutable_data and (mutable_data['paid'] is False or str(mutable_data['paid']).lower() in ['false', '0']):
            mutable_data['price'] = '0.00'

        # Support 'key_features' or 'features' alias for 'highlights'
        if hasattr(data, 'getlist'):
            hl = data.getlist('highlights') or data.getlist('key_features') or data.getlist('features')
            if hl and len(hl) > 1:
                mutable_data['highlights'] = hl
            elif not mutable_data.get('highlights'):
                if mutable_data.get('key_features'):
                    mutable_data['highlights'] = mutable_data['key_features']
                elif mutable_data.get('features'):
                    mutable_data['highlights'] = mutable_data['features']
        else:
            if not mutable_data.get('highlights'):
                discrete_hls = []
                for i in range(1, 6):
                    for k in [f'highlight_{i}', f'highlight{i}', f'point_{i}']:
                        if mutable_data.get(k):
                            discrete_hls.append(str(mutable_data[k]).strip())
                            break
                if discrete_hls:
                    mutable_data['highlights'] = discrete_hls
                elif mutable_data.get('key_features'):
                    mutable_data['highlights'] = mutable_data['key_features']
                elif mutable_data.get('features'):
                    mutable_data['highlights'] = mutable_data['features']

        # Parse highlights if passed as JSON string or multi-line string
        highlights = mutable_data.get('highlights')
        if isinstance(highlights, str):
            import json
            try:
                mutable_data['highlights'] = json.loads(highlights)
            except Exception:
                items = [h.strip() for h in highlights.replace('\r\n', '\n').split('\n') if h.strip()]
                mutable_data['highlights'] = items

        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        title = attrs.get('title') or (self.instance and self.instance.title)
        if not title or not str(title).strip():
            raise serializers.ValidationError({'title': 'Title is required.'})
        if not attrs.get('category') and not (self.instance and self.instance.category):
            raise serializers.ValidationError({'category': 'Resource category is required. A category must be created or selected before adding a resource.'})

        # Validate resource_type
        rt = attrs.get('resource_type') or (self.instance and getattr(self.instance, 'resource_type', None))
        if rt and rt not in ['note', 'question paper']:
            raise serializers.ValidationError({
                'resource_type': "Resource type must be either 'note' or 'question paper'."
            })

        # Validate price
        price_val = attrs.get('price')
        if price_val is not None:
            try:
                from decimal import Decimal
                d = Decimal(str(price_val))
                if d < Decimal('0.00'):
                    raise serializers.ValidationError({'price': 'Price cannot be negative.'})
                attrs['price'] = d
            except Exception:
                raise serializers.ValidationError({'price': 'A valid price number is required.'})

        cleaned_title = ' '.join(str(title).strip().split())
        attrs['title'] = cleaned_title

        title_slug = slugify(cleaned_title)
        existing_qs = PaidResource.objects.filter(is_deleted=False).filter(
            models.Q(title__iexact=cleaned_title) | models.Q(slug__iexact=title_slug)
        )
        if self.instance:
            existing_qs = existing_qs.exclude(pk=self.instance.pk)

        if existing_qs.exists():
            raise serializers.ValidationError({
                'title': f"A resource with the title '{cleaned_title}' already exists."
            })

        return attrs


class ResourcePDFUploadSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    uploaded_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = ResourcePDF
        fields = ('id', 'resource', 'file', 'title', 'file_size', 'is_active', 'uploaded_at')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        return ret


class ResourcePurchaseFileSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ResourcePDF
        fields = ('id', 'title', 'file', 'file_url', 'file_size')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        return ret


class ResourcePurchaseSerializer(serializers.ModelSerializer):
    from apps.resources.models import ResourcePurchase
    resource_id = serializers.IntegerField(source='resource.id', read_only=True)
    title = serializers.CharField(source='resource.title', read_only=True)
    slug = serializers.CharField(source='resource.slug', read_only=True)
    resource_type = serializers.CharField(source='resource.resource_type', read_only=True)
    category = serializers.CharField(source='resource.category', read_only=True)
    description = serializers.CharField(source='resource.description', read_only=True)
    highlights = serializers.JSONField(source='resource.highlights', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    purchased_date_formatted = serializers.SerializerMethodField()
    access_url = serializers.SerializerMethodField()
    pdf_count = serializers.IntegerField(source='resource.pdf_count', read_only=True)
    files = serializers.SerializerMethodField()

    class Meta:
        from apps.resources.models import ResourcePurchase
        model = ResourcePurchase
        fields = (
            'id', 'resource_id', 'title', 'slug', 'resource_type', 'category', 'description',
            'highlights', 'status', 'status_display',
            'payment_status', 'payment_method',
            'amount_paid', 'currency', 'order_id',
            'purchased_at', 'purchased_date_formatted',
            'download_count', 'last_accessed_at',
            'access_url', 'pdf_count', 'files',
            'created_at', 'updated_at'
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_purchased_date_formatted(self, obj):
        if obj.purchased_at:
            day = obj.purchased_at.strftime('%d').lstrip('0')
            month_year = obj.purchased_at.strftime('%b %Y')
            return f"Purchased {day} {month_year}"
        return ""

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_access_url(self, obj):
        request = self.context.get('request')
        first_pdf = obj.resource.pdf_files.filter(is_deleted=False).first()
        if first_pdf and first_pdf.file:
            if request:
                return request.build_absolute_uri(first_pdf.file.url)
            return first_pdf.file.url
        return None

    @extend_schema_field(ResourcePurchaseFileSerializer(many=True))
    def get_files(self, obj):
        request = self.context.get('request')
        pdfs = obj.resource.pdf_files.filter(is_deleted=False)
        return ResourcePurchaseFileSerializer(pdfs, many=True, context={'request': request}).data


class StudentPurchasedResourceFileSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    file = serializers.SerializerMethodField()

    class Meta:
        model = ResourcePDF
        fields = ('id', 'title', 'file', 'file_size')

    @extend_schema_field(serializers.CharField())
    def get_file(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, 'uuid'):
            ret['id'] = str(instance.uuid)
        return ret


class StudentPurchasedResourceCardSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Student Purchased Resources list.
    Returns: id, resource_id, category, title, description, purchased_date, files.
    """
    resource_id = serializers.IntegerField(source='resource.id', read_only=True)
    resource_type = serializers.CharField(source='resource.resource_type', read_only=True)
    category = serializers.CharField(source='resource.category', read_only=True)
    title = serializers.CharField(source='resource.title', read_only=True)
    description = serializers.CharField(source='resource.description', read_only=True)
    purchased_date = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()

    class Meta:
        from apps.resources.models import ResourcePurchase
        model = ResourcePurchase
        fields = (
            'id',
            'resource_id',
            'resource_type',
            'category',
            'title',
            'description',
            'purchased_date',
            'files',
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_purchased_date(self, obj):
        if obj.purchased_at:
            day = obj.purchased_at.strftime('%d').lstrip('0')
            month_year = obj.purchased_at.strftime('%b %Y')
            return f"{day} {month_year}"
        return ""

    @extend_schema_field(StudentPurchasedResourceFileSerializer(many=True))
    def get_files(self, obj):
        request = self.context.get('request')
        pdfs = obj.resource.pdf_files.filter(is_deleted=False).order_by('-id')
        return StudentPurchasedResourceFileSerializer(pdfs, many=True, context={'request': request}).data


class StudentPurchasedResourceDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for single student purchased resource page matching UI:
    - Top header with badges (Verified Material, Full Access Unlocked, Lifetime Student Access, Syllabus Blueprint Mapped)
    - 4 Metadata specs (Format, Target Exams, Language, Questions / Notes)
    - Right action panel (Open Reader, View Modules, Ask Faculty)
    - Tab 1: Interactive Study Reader (Live mock question, rationales, package coverage, doubt support)
    - Tab 2: Included Papers & Modules (5 complete modules with questions/duration)
    - Tab 3: Exam Blueprint & Strategy (Licensing blueprint with topic weightages)
    - Downloadable PDF files
    """
    resource_id = serializers.IntegerField(source='resource.id', read_only=True)
    resource_type = serializers.CharField(source='resource.resource_type', read_only=True)
    category = serializers.CharField(source='resource.category', read_only=True)
    title = serializers.CharField(source='resource.title', read_only=True)
    description = serializers.CharField(source='resource.description', read_only=True)
    purchased_date = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    payment_status = serializers.CharField(read_only=True)
    badges = serializers.SerializerMethodField()
    specifications = serializers.SerializerMethodField()
    resource_access_actions = serializers.SerializerMethodField()
    interactive_study_reader = serializers.SerializerMethodField()
    included_modules = serializers.SerializerMethodField()
    blueprint_strategy = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()

    class Meta:
        from apps.resources.models import ResourcePurchase
        model = ResourcePurchase
        fields = (
            'id',
            'resource_id',
            'resource_type',
            'category',
            'title',
            'description',
            'purchased_date',
            'status',
            'payment_status',
            'badges',
            'specifications',
            'resource_access_actions',
            'interactive_study_reader',
            'included_modules',
            'blueprint_strategy',
            'files',
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_purchased_date(self, obj):
        if obj.purchased_at:
            day = obj.purchased_at.strftime('%d').lstrip('0')
            month_year = obj.purchased_at.strftime('%b %Y')
            return f"{day} {month_year}"
        return ""

    @extend_schema_field(serializers.DictField())
    def get_badges(self, obj):
        return {
            "verified_material": "Verified Material",
            "access_status": "Full Access Unlocked",
            "tags": ["Lifetime Student Access", "Syllabus Blueprint Mapped"]
        }

    @extend_schema_field(serializers.DictField())
    def get_specifications(self, obj):
        return {
            "format": "Interactive Online Reader",
            "target_exams": "DHA / MOH / PSC",
            "language": "English & Bilingual",
            "questions_notes": "Full Pack Included"
        }

    @extend_schema_field(serializers.DictField())
    def get_resource_access_actions(self, obj):
        return {
            "actions": [
                {"key": "open_reader", "label": "Open In-Browser Reader", "type": "primary"},
                {"key": "view_modules", "label": "View Included Modules", "type": "secondary"},
                {"key": "ask_faculty", "label": "Ask Faculty / Mentor", "type": "link"}
            ],
            "notice": "All study material, worked solutions, and blueprint notes are accessible in this portal."
        }

    @extend_schema_field(serializers.DictField())
    def get_interactive_study_reader(self, obj):
        return {
            "tab_title": "Interactive Study Reader",
            "paper_title": "Paper 1: High-Yield Practice Mock Exam",
            "paper_subtitle": "Interactive practice with worked explanations",
            "mode": "Live Study Mode",
            "total_questions": 150,
            "showing_text": "Showing 3 of 150 practice items",
            "current_question": {
                "question_number": 2,
                "question_text": "In Westgard Multirule quality control evaluation, which rule is considered a warning rule triggering inspection rather than an immediate run rejection?",
                "options": [
                    {"id": "A", "text": "1_3s rule (One control measurement exceeds +/- 3SD)"},
                    {"id": "B", "text": "1_2s rule (One control measurement exceeds +/- 2SD)"},
                    {"id": "C", "text": "2_2s rule (Two consecutive control measurements exceed +/- 2SD)"},
                    {"id": "D", "text": "R_4s rule (Difference between consecutive controls exceeds 4SD)"}
                ],
                "correct_option": "B",
                "rationale": "The 1_2s rule is commonly used as a warning/screening rule in Westgard algorithms to trigger inspection of subsequent runs."
            },
            "coverage_in_package": [
                "High-yield biochemistry notes",
                "Clinical case correlations",
                "Instrumentation quick charts",
                "QC & method validation guide",
                "Exam-focused mnemonics"
            ],
            "faculty_support": {
                "title": "Stuck on a tricky question?",
                "subtitle": "Our faculty and exam-cleared alumni conduct weekly live doubt sessions for students.",
                "button_text": "Submit Question to Faculty"
            }
        }

    @extend_schema_field(serializers.DictField())
    def get_included_modules(self, obj):
        return {
            "tab_title": "Included Papers & Modules (5)",
            "title": "Complete Module Breakdown",
            "subtitle": "All mock papers, solved keys, and revision guides included in this pack.",
            "count": 5,
            "modules": [
                {
                    "part": "Part 1",
                    "badge": "150 Questions",
                    "title": "Module 1: Prometric Blueprint Diagnostic Mock 1",
                    "description": "Full examination covering Clinical Pathology, Biochemistry, Microbiology, and Immunohematology.",
                    "duration": "180 Mins",
                    "action": "Study in Reader"
                },
                {
                    "part": "Part 2",
                    "badge": "150 Questions",
                    "title": "Module 2: Prometric Blueprint Diagnostic Mock 2",
                    "description": "Timed simulation mapped to DHA & HAAD exam weightages with difficulty tagging.",
                    "duration": "180 Mins",
                    "action": "Study in Reader"
                },
                {
                    "part": "Part 3",
                    "badge": "500+ Questions",
                    "title": "Module 3: Ten-Year Solved Question Archive",
                    "description": "Past actual exam papers fully solved with detailed clinical rationales.",
                    "duration": "Self-Paced",
                    "action": "Study in Reader"
                },
                {
                    "part": "Part 4",
                    "badge": "Comprehensive Guide",
                    "title": "Module 4: Quality Control & Instrumentation Quick Sheet",
                    "description": "Westgard rules, calibration algorithms, and pre-analytical error troubleshooting.",
                    "duration": "45 Mins Read",
                    "action": "Study in Reader"
                },
                {
                    "part": "Part 5",
                    "badge": "Full Key",
                    "title": "Module 5: Clinical Rationales & Explanations Handbook",
                    "description": "Step-by-step logic for every question with official healthcare board references.",
                    "duration": "Reference Book",
                    "action": "Study in Reader"
                }
            ]
        }

    @extend_schema_field(serializers.DictField())
    def get_blueprint_strategy(self, obj):
        return {
            "tab_title": "Exam Blueprint & Strategy",
            "title": "Licensing Blueprint & Topic Weightage",
            "subtitle": "Exam preparation distribution recommended by Avemaria academic advisors.",
            "topics": [
                {
                    "topic": "Clinical Biochemistry",
                    "weightage": "25%",
                    "summary": "Enzymes, Electrolytes, Acid-Base, Lipids, Hormones, Quality Control"
                },
                {
                    "topic": "Hematology & Coagulation",
                    "weightage": "25%",
                    "summary": "Anemias, Leukemias, Coagulation cascade, Peripheral smear morphology"
                },
                {
                    "topic": "Microbiology & Parasitology",
                    "weightage": "20%",
                    "summary": "Gram-positive/negative bacteria, Culture media, Antibiotic susceptibility"
                },
                {
                    "topic": "Blood Banking & Serology",
                    "weightage": "15%",
                    "summary": "ABO/Rh grouping, Cross-matching, Transfusion reactions, ELISA, Rapid tests"
                },
                {
                    "topic": "Histopathology & Cytology",
                    "weightage": "10%",
                    "summary": "Tissue fixation, Processing, Staining techniques, Pap smear basics"
                },
                {
                    "topic": "Lab Safety & Ethics",
                    "weightage": "5%",
                    "summary": "Biohazard safety, Disinfection, Biomedical waste management, Good lab practices"
                }
            ]
        }

    @extend_schema_field(StudentPurchasedResourceFileSerializer(many=True))
    def get_files(self, obj):
        request = self.context.get('request')
        pdfs = obj.resource.pdf_files.filter(is_deleted=False).order_by('-id')
        return StudentPurchasedResourceFileSerializer(pdfs, many=True, context={'request': request}).data


class StudentPurchaseHistorySerializer(serializers.ModelSerializer):
    """
    Serializer specifically modeled for the Student Purchase History Table:
    Columns: SL. NO | ITEM / RESOURCE | DATE | AMOUNT | REFERENCE | STATUS | RECEIPT / INVOICE
    """
    id = serializers.IntegerField(read_only=True)
    resource_id = serializers.IntegerField(source='resource.id', read_only=True)
    resource = serializers.CharField(source='resource.title', read_only=True)
    resource_type = serializers.CharField(source='resource.resource_type', read_only=True)
    category = serializers.CharField(source='resource.category', read_only=True)
    date = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()
    status = serializers.CharField(source='payment_status', read_only=True)
    invoice = serializers.SerializerMethodField()
    purchased_at = serializers.DateTimeField(read_only=True)

    class Meta:
        from apps.resources.models import ResourcePurchase
        model = ResourcePurchase
        fields = (
            'id',
            'resource_id',
            'resource',
            'resource_type',
            'category',
            'date',
            'amount',
            'reference',
            'status',
            'invoice',
            'purchased_at'
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_date(self, obj):
        if obj.purchased_at:
            day = obj.purchased_at.strftime('%d').lstrip('0')
            month_year = obj.purchased_at.strftime('%b %Y')
            return f"{day} {month_year}"
        return ""

    @extend_schema_field(serializers.CharField())
    def get_amount(self, obj):
        curr = obj.currency or '£'
        val = obj.amount_paid if obj.amount_paid is not None else 0.00
        return f"{curr}{val:.2f}"

    @extend_schema_field(serializers.CharField())
    def get_reference(self, obj):
        if obj.order_id:
            return obj.order_id
        return f"DEMO-{obj.id:04d}"

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_invoice(self, obj):
        request = self.context.get('request')
        first_pdf = obj.resource.pdf_files.filter(is_deleted=False).first()
        if first_pdf and first_pdf.file:
            if request:
                return request.build_absolute_uri(first_pdf.file.url)
            return first_pdf.file.url
        return None


class StudentPaymentDetailItemSerializer(serializers.ModelSerializer):
    """
    Serializer matching the Payment Details transaction row:
    Left: Resource Title
    Right: demo · DEMO-0001 · £15.00
    """
    resource_id = serializers.IntegerField(source='resource.id', read_only=True)
    resource_title = serializers.CharField(source='resource.title', read_only=True)
    resource_slug = serializers.CharField(source='resource.slug', read_only=True)
    resource_type = serializers.CharField(source='resource.resource_type', read_only=True)
    category = serializers.CharField(source='resource.category', read_only=True)
    amount = serializers.DecimalField(source='amount_paid', max_digits=10, decimal_places=2, read_only=True)
    amount_formatted = serializers.SerializerMethodField()
    status = serializers.CharField(source='payment_status', read_only=True)
    payment_line = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()

    class Meta:
        from apps.resources.models import ResourcePurchase
        model = ResourcePurchase
        fields = (
            'id',
            'resource_id',
            'resource_title',
            'resource_slug',
            'resource_type',
            'category',
            'payment_method',
            'order_id',
            'amount',
            'amount_formatted',
            'currency',
            'status',
            'payment_line',
            'date',
            'purchased_at'
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_amount_formatted(self, obj):
        curr = obj.currency or '£'
        val = obj.amount_paid if obj.amount_paid is not None else 0.00
        return f"{curr}{val:.2f}"

    @extend_schema_field(serializers.CharField())
    def get_payment_line(self, obj):
        method = obj.payment_method or 'demo'
        ref = obj.order_id or f"DEMO-{obj.id:04d}"
        curr = obj.currency or '£'
        val = obj.amount_paid if obj.amount_paid is not None else 0.00
        return f"{method} · {ref} · {curr}{val:.2f}"

    @extend_schema_field(serializers.CharField())
    def get_date(self, obj):
        if obj.purchased_at:
            day = obj.purchased_at.strftime('%d').lstrip('0')
            month_year = obj.purchased_at.strftime('%b %Y')
            return f"{day} {month_year}"
        return ""


class StudentReceiptSerializer(serializers.ModelSerializer):
    """
    Serializer matching the Receipts / Invoices list interface:
    id, receipt_number, resource_id, resource_title, category, date, amount_paid, payment_status, purchased_at
    """
    id = serializers.IntegerField(read_only=True)
    receipt_number = serializers.SerializerMethodField()
    resource_id = serializers.IntegerField(source='resource.id', read_only=True)
    resource_title = serializers.CharField(source='resource.title', read_only=True)
    resource_type = serializers.CharField(source='resource.resource_type', read_only=True)
    category = serializers.CharField(source='resource.category', read_only=True)
    date = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()
    payment_status = serializers.CharField(read_only=True)
    purchased_at = serializers.DateTimeField(read_only=True)

    class Meta:
        from apps.resources.models import ResourcePurchase
        model = ResourcePurchase
        fields = (
            'id',
            'receipt_number',
            'resource_id',
            'resource_title',
            'resource_type',
            'category',
            'date',
            'amount_paid',
            'payment_status',
            'purchased_at'
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_receipt_number(self, obj):
        if obj.receipt_number:
            return obj.receipt_number
        return f"INV-{obj.id:05d}"

    @extend_schema_field(serializers.CharField())
    def get_date(self, obj):
        if obj.purchased_at:
            day = obj.purchased_at.strftime('%d').lstrip('0')
            month_year = obj.purchased_at.strftime('%b %Y')
            return f"{day} {month_year}"
        return ""

    @extend_schema_field(serializers.CharField())
    def get_amount_paid(self, obj):
        val = obj.amount_paid if obj.amount_paid is not None else 0.00
        return f"{val:.2f}"


class StudentSingleReceiptDetailSerializer(serializers.ModelSerializer):
    """
    Serializer matching the single Tax Invoice & Receipt Modal:
    - receipt_number: e.g. "INV-2026-4DE30E"
    - date: "31 Aug 2026"
    - billed_to: { name, email, account_type, program }
    - payment_summary: { payment_method, reference, payment_status }
    - items: [ { description, summary, category, qty, price, total } ]
    - subtotal: "£15.00"
    - vat_text: "VAT (0% Educational Exemption)"
    - vat_amount: "£0.00"
    - total_paid: "£15.00"
    - security_note: "Verified 256-bit SSL encrypted digital tax receipt."
    - official_receipt: { title, message, badge }
    - pdf_url: download url
    """
    id = serializers.IntegerField(read_only=True)
    receipt_number = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    billed_to = serializers.SerializerMethodField()
    payment_summary = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    vat_text = serializers.SerializerMethodField()
    vat_amount = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    security_note = serializers.SerializerMethodField()
    official_receipt = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    purchased_at = serializers.DateTimeField(read_only=True)

    class Meta:
        from apps.resources.models import ResourcePurchase
        model = ResourcePurchase
        fields = (
            'id',
            'receipt_number',
            'date',
            'billed_to',
            'payment_summary',
            'items',
            'subtotal',
            'vat_text',
            'vat_amount',
            'total_paid',
            'security_note',
            'official_receipt',
            'pdf_url',
            'purchased_at'
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_receipt_number(self, obj):
        if obj.receipt_number:
            return obj.receipt_number
        return f"INV-2026-{obj.id:04X}"

    @extend_schema_field(serializers.CharField())
    def get_date(self, obj):
        if obj.purchased_at:
            day = obj.purchased_at.strftime('%d').lstrip('0')
            month_year = obj.purchased_at.strftime('%b %Y')
            return f"{day} {month_year}"
        return ""

    @extend_schema_field(serializers.DictField())
    def get_billed_to(self, obj):
        student = obj.student
        email = student.email or (student.user.email if student.user else "")
        program = student.qualification or "Healthcare Licensing Program"
        if not program:
            program = "Healthcare Licensing Program"
        return {
            "name": student.name,
            "email": email,
            "account_type": "Student Account",
            "program": program
        }

    @extend_schema_field(serializers.DictField())
    def get_payment_summary(self, obj):
        method = obj.payment_method or "demo"
        ref = obj.order_id or f"DEMO-{obj.id:04d}"
        status_display = "Payment Completed" if obj.payment_status == "paid" else obj.get_payment_status_display()
        return {
            "payment_method": method,
            "reference": f"Ref: {ref}",
            "payment_status": status_display
        }

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_items(self, obj):
        curr = obj.currency or "£"
        val = obj.amount_paid if obj.amount_paid is not None else (obj.resource.price or 0.00)
        formatted_price = f"{curr}{val:.2f}"
        return [
            {
                "description": obj.resource.title,
                "summary": obj.resource.description or "Condensed analyte, Instrumentation and quality-control notes written for licensing candidates.",
                "category": obj.resource.category or "Notes",
                "resource_type": getattr(obj.resource, 'resource_type', 'note'),
                "qty": 1,
                "price": formatted_price,
                "total": formatted_price
            }
        ]

    @extend_schema_field(serializers.CharField())
    def get_subtotal(self, obj):
        curr = obj.currency or "£"
        val = obj.amount_paid if obj.amount_paid is not None else 0.00
        return f"{curr}{val:.2f}"

    @extend_schema_field(serializers.CharField())
    def get_vat_text(self, obj):
        return "VAT (0% Educational Exemption)"

    @extend_schema_field(serializers.CharField())
    def get_vat_amount(self, obj):
        curr = obj.currency or "£"
        return f"{curr}0.00"

    @extend_schema_field(serializers.CharField())
    def get_total_paid(self, obj):
        curr = obj.currency or "£"
        val = obj.amount_paid if obj.amount_paid is not None else 0.00
        return f"{curr}{val:.2f}"

    @extend_schema_field(serializers.CharField())
    def get_security_note(self, obj):
        return "Verified 256-bit SSL encrypted digital tax receipt."

    @extend_schema_field(serializers.DictField())
    def get_official_receipt(self, obj):
        return {
            "title": "OFFICIAL PAID RECEIPT",
            "message": "Thank you for your enrollment. Your access has been provisioned.",
            "badge": "VERIFIED"
        }

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_pdf_url(self, obj):
        request = self.context.get('request')
        first_pdf = obj.resource.pdf_files.filter(is_deleted=False).first()
        if first_pdf and first_pdf.file:
            if request:
                return request.build_absolute_uri(first_pdf.file.url)
            return first_pdf.file.url
        return None


class DeletePdfResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class DeleteCategoryResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class PurchasedResourcesResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = ResourcePurchaseSerializer(many=True)


class PurchaseHistoryResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = StudentPurchaseHistorySerializer(many=True)


class PaymentDetailsSummarySerializer(serializers.Serializer):
    total_spent = serializers.CharField()
    total_spent_formatted = serializers.CharField()
    currency = serializers.CharField()
    completed_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    total_transactions = serializers.IntegerField()


class PaymentDetailsNoticeSerializer(serializers.Serializer):
    title = serializers.CharField()
    note = serializers.CharField()


class PaymentDetailsResponseSerializer(serializers.Serializer):
    total_spent = serializers.CharField()
    completed_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    results = StudentPaymentDetailItemSerializer(many=True)


class ReceiptsListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = StudentReceiptSerializer(many=True)




