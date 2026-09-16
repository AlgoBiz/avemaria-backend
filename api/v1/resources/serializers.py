from collections import OrderedDict
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.resources.models import PaidResource, ResourcePDF, ResourceCategory

class ResourceCategorySerializer(serializers.ModelSerializer):
    resources_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ResourceCategory
        fields = ('id', 'name', 'resources_count', 'is_active', 'is_deleted', 'created_at', 'updated_at')
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


class ResourcePDFSerializer(serializers.ModelSerializer):
    uploaded_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = ResourcePDF
        fields = ('id', 'title', 'file', 'file_size', 'is_active', 'is_deleted', 'uploaded_at', 'created_at')


class ResourceListSerializer(serializers.ModelSerializer):
    pdf_count = serializers.IntegerField(read_only=True)
    pdf_count_display = serializers.SerializerMethodField()
    highlights = serializers.JSONField(read_only=True)

    class Meta:
        model = PaidResource
        fields = (
            'id',
            'category',
            'price',
            'title',
            'description',
            'highlights',
            'pdf_count',
            'pdf_count_display'
        )

    @extend_schema_field(serializers.CharField())
    def get_pdf_count_display(self, obj):
        return f"{obj.pdf_count} PDFs attached"

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ordered_ret = OrderedDict()
        for field in self.Meta.fields:
            if field in ret:
                ordered_ret[field] = ret[field]
        return ordered_ret


class PaidResourceSerializer(serializers.ModelSerializer):
    pdf_files = ResourcePDFSerializer(many=True, read_only=True)
    pdf_count = serializers.IntegerField(read_only=True)
    category = serializers.CharField(required=True, allow_blank=False)
    pdf_count_display = serializers.SerializerMethodField()
    highlights = serializers.JSONField(required=False, default=list)

    class Meta:
        model = PaidResource
        fields = (
            'id',
            'category',
            'price',
            'title',
            'description',
            'highlights',
            'pdf_count',
            'pdf_count_display',
            'pdf_files',
            'course_name',
            'is_active',
            'is_deleted',
            'created_at',
            'updated_at'
        )
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'is_deleted': {'default': False, 'required': False},
            'course_name': {'required': False, 'allow_blank': True}
        }

    @extend_schema_field(serializers.CharField())
    def get_price_formatted(self, obj):
        if obj.price == 0:
            return 'Free'
        curr = obj.currency or '£'
        return f"{curr}{obj.price:.2f}"

    @extend_schema_field(serializers.CharField())
    def get_pdf_count_display(self, obj):
        return f"{obj.pdf_count} PDFs attached"

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ordered_ret = OrderedDict()
        for field in self.Meta.fields:
            if field in ret:
                ordered_ret[field] = ret[field]
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
            for alias in ['category_name', 'resource_category', 'type']:
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

        # Clean up price string (e.g. "£29.00", "Free", "$29.00")
        price = mutable_data.get('price')
        if price is not None:
            if isinstance(price, str):
                cleaned_price = price.strip()
                if cleaned_price.lower() in ['free', 'free of cost', 'nil', '']:
                    mutable_data['price'] = '0.00'
                else:
                    cleaned_price = cleaned_price.replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                    mutable_data['price'] = cleaned_price

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
        if not attrs.get('title') and not (self.instance and self.instance.title):
            raise serializers.ValidationError({'title': 'Title is required.'})
        if not attrs.get('category') and not (self.instance and self.instance.category):
            raise serializers.ValidationError({'category': 'Resource category is required. A category must be created or selected before adding a resource.'})
        return attrs


class ResourcePDFUploadSerializer(serializers.ModelSerializer):
    uploaded_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = ResourcePDF
        fields = ('id', 'resource', 'file', 'title', 'file_size', 'is_active', 'uploaded_at')


class ResourcePurchaseFileSerializer(serializers.ModelSerializer):
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


class ResourcePurchaseSerializer(serializers.ModelSerializer):
    from apps.resources.models import ResourcePurchase
    resource_id = serializers.IntegerField(source='resource.id', read_only=True)
    title = serializers.CharField(source='resource.title', read_only=True)
    slug = serializers.CharField(source='resource.slug', read_only=True)
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
            'id', 'resource_id', 'title', 'slug', 'category', 'description',
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


class StudentPurchasedResourceCardSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Student Purchased Resources list.
    Returns: id, resource_id, category, title, description, purchased_date, files.
    """
    resource_id = serializers.IntegerField(source='resource.id', read_only=True)
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


class StudentPurchaseHistorySerializer(serializers.ModelSerializer):
    """
    Serializer specifically modeled for the Student Purchase History Table:
    Columns: SL. NO | RESOURCE | DATE | AMOUNT | STATUS
    """
    sl_no = serializers.IntegerField(read_only=True, default=1)
    resource = serializers.CharField(source='resource.title', read_only=True)
    resource_id = serializers.IntegerField(source='resource.id', read_only=True)
    resource_slug = serializers.CharField(source='resource.slug', read_only=True)
    category = serializers.CharField(source='resource.category', read_only=True)
    date = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    status = serializers.CharField(source='payment_status', read_only=True)
    payment_status = serializers.CharField(read_only=True)
    payment_method = serializers.CharField(read_only=True)
    access_url = serializers.SerializerMethodField()

    class Meta:
        from apps.resources.models import ResourcePurchase
        model = ResourcePurchase
        fields = (
            'sl_no',
            'id',
            'resource_id',
            'resource',
            'resource_slug',
            'category',
            'date',
            'amount',
            'amount_paid',
            'currency',
            'status',
            'payment_status',
            'payment_method',
            'order_id',
            'access_url',
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

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_access_url(self, obj):
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
    Left Title: Resource Title
    Left Subtitle: 31 Aug 2026 · £15.00
    Right Status: "Receipt emailed to you"
    """
    resource_id = serializers.IntegerField(source='resource.id', read_only=True)
    resource_title = serializers.CharField(source='resource.title', read_only=True)
    resource_slug = serializers.CharField(source='resource.slug', read_only=True)
    category = serializers.CharField(source='resource.category', read_only=True)
    date = serializers.SerializerMethodField()
    amount_formatted = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    receipt_status_text = serializers.SerializerMethodField()
    access_url = serializers.SerializerMethodField()

    class Meta:
        from apps.resources.models import ResourcePurchase
        model = ResourcePurchase
        fields = (
            'id',
            'receipt_number',
            'resource_id',
            'resource_title',
            'resource_slug',
            'category',
            'date',
            'amount_paid',
            'amount_formatted',
            'currency',
            'payment_status',
            'payment_method',
            'subtitle',
            'receipt_status_text',
            'receipt_emailed',
            'receipt_emailed_at',
            'access_url',
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
    def get_amount_formatted(self, obj):
        curr = obj.currency or '£'
        val = obj.amount_paid if obj.amount_paid is not None else 0.00
        return f"{curr}{val:.2f}"

    @extend_schema_field(serializers.CharField())
    def get_subtitle(self, obj):
        date_str = self.get_date(obj)
        amt_str = self.get_amount_formatted(obj)
        return f"{date_str} · {amt_str}"

    @extend_schema_field(serializers.CharField())
    def get_receipt_status_text(self, obj):
        if obj.receipt_emailed:
            return "Receipt emailed to you"
        if obj.payment_status == 'paid':
            return "Receipt emailed to you"
        return "Pending payment"

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_access_url(self, obj):
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
    summary = PaymentDetailsSummarySerializer()
    payment_methods_notice = PaymentDetailsNoticeSerializer()
    results = StudentPaymentDetailItemSerializer(many=True)


class ReceiptsListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = StudentReceiptSerializer(many=True)




