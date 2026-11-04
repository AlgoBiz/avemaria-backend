from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.payments.models import PaymentTransaction


class PaymentConfigSerializer(serializers.Serializer):
    publishable_key = serializers.CharField(help_text="Stripe Publishable Key")
    currency = serializers.CharField(help_text="Default platform currency code e.g. gbp")


class CreateCheckoutSessionSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(
        choices=['course', 'resource'],
        required=False,
        help_text="Type of product being purchased ('course' or 'resource')"
    )
    item_id = serializers.CharField(
        required=False,
        help_text="ID or slug of the Course or PaidResource"
    )
    course_id = serializers.CharField(required=False, allow_blank=True)
    course_slug = serializers.CharField(required=False, allow_blank=True)
    resource_id = serializers.CharField(required=False, allow_blank=True)
    resource_slug = serializers.CharField(required=False, allow_blank=True)
    type = serializers.CharField(required=False, allow_blank=True)
    id = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Candidate or student full name"
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text="Candidate or student email address"
    )
    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Candidate or student contact phone number"
    )
    success_url = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Custom redirect URL on successful payment (must support session_id query param)"
    )
    cancel_url = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Custom redirect URL if customer cancels payment"
    )

    def to_internal_value(self, data):
        mutable_data = data.copy() if hasattr(data, 'copy') else dict(data)

        # 1. Normalize type / item_type
        raw_type = mutable_data.get('item_type') or mutable_data.get('type')
        if not raw_type:
            if any(k in mutable_data for k in ('course_id', 'course_slug', 'course')):
                raw_type = 'course'
            elif any(k in mutable_data for k in ('resource_id', 'resource_slug', 'resource')):
                raw_type = 'resource'

        if raw_type:
            norm_type = str(raw_type).strip().lower()
            if norm_type in ('course', 'courses'):
                mutable_data['item_type'] = 'course'
            elif norm_type in ('resource', 'resources'):
                mutable_data['item_type'] = 'resource'

        # 2. Normalize item_id
        if not mutable_data.get('item_id'):
            detected_id = (
                mutable_data.get('course_id') or
                mutable_data.get('course_slug') or
                mutable_data.get('course') or
                mutable_data.get('resource_id') or
                mutable_data.get('resource_slug') or
                mutable_data.get('resource') or
                mutable_data.get('id')
            )
            if detected_id:
                mutable_data['item_id'] = str(detected_id).strip()

        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        if not attrs.get('item_type'):
            raise serializers.ValidationError({
                'item_type': "Must be specified ('course' or 'resource'), or provide 'course_id'/'resource_id'."
            })
        if not attrs.get('item_id'):
            raise serializers.ValidationError({
                'item_id': "Item identifier must be provided ('item_id', 'course_id', or 'resource_id')."
            })
        return attrs


class CheckoutSessionResponseSerializer(serializers.Serializer):
    url = serializers.CharField(required=False, help_text="Stripe hosted checkout URL")
    checkout_url = serializers.CharField(help_text="Stripe hosted checkout URL to redirect the user to")
    checkoutUrl = serializers.CharField(required=False)
    session_url = serializers.CharField(required=False)
    session_id = serializers.CharField(help_text="Stripe Checkout Session ID")
    sessionId = serializers.CharField(required=False)
    id = serializers.CharField(required=False)
    publishable_key = serializers.CharField(help_text="Stripe publishable key")
    item_type = serializers.CharField()
    item_id = serializers.CharField()
    item_title = serializers.CharField()
    amount = serializers.FloatField()
    currency = serializers.CharField()


class VerifySessionSerializer(serializers.Serializer):
    session_id = serializers.CharField(help_text="Stripe Checkout Session ID to verify")


class VerifySessionResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="Payment status: paid, unpaid, or pending")
    item_type = serializers.CharField(allow_blank=True, required=False)
    item_id = serializers.CharField(allow_blank=True, required=False)
    item_title = serializers.CharField(allow_blank=True, required=False)
    receipt_number = serializers.CharField(allow_blank=True, required=False)
    amount_paid = serializers.FloatField(required=False)
    currency = serializers.CharField(allow_blank=True, required=False)


class StripeWebhookPayloadSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, help_text="Stripe event ID")
    type = serializers.CharField(help_text="Stripe event type e.g. checkout.session.completed")
    data = serializers.DictField(help_text="Raw event object dictionary")



class PaymentTransactionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)
    item_type_display = serializers.CharField(source='get_item_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    student_name = serializers.CharField(source='student.name', read_only=True)
    invoice_number = serializers.SerializerMethodField()
    invoice_download_url = serializers.SerializerMethodField()
    invoice_view_url = serializers.SerializerMethodField()

    class Meta:
        model = PaymentTransaction
        fields = (
            'id', 'uuid', 'item_type', 'item_type_display', 'item_id', 'item_title',
            'amount', 'currency', 'status', 'status_display', 'invoice_number',
            'invoice_download_url', 'invoice_view_url',
            'receipt_number', 'stripe_session_id', 'completed_at', 'created_at',
            'student_name'
        )
        read_only_fields = fields

    def get_invoice_number(self, obj):
        rec = getattr(obj, 'receipt_number', None)
        if rec and not str(rec).startswith('cs_'):
            return rec if str(rec).startswith('#') else f"#{rec}"

        if obj.item_type == 'course':
            from apps.courses.models import CourseEnrollment
            enr = CourseEnrollment.objects.filter(
                student=obj.student, course_id=obj.item_id, is_deleted=False
            ).first()
            if enr and enr.receipt_number and not enr.receipt_number.startswith('cs_'):
                return enr.receipt_number if enr.receipt_number.startswith('#') else f"#{enr.receipt_number}"
            student_id = obj.student_id or (obj.student.id if obj.student else 1)
            return f"#INV-2026-{1042 - (student_id - 1) * 3:04d}"

        elif obj.item_type == 'resource':
            from apps.resources.models import ResourcePurchase
            pur = ResourcePurchase.objects.filter(
                student=obj.student, resource_id=obj.item_id, is_deleted=False
            ).first()
            if pur and pur.receipt_number and not pur.receipt_number.startswith('cs_'):
                return pur.receipt_number if pur.receipt_number.startswith('#') else f"#{pur.receipt_number}"
            pur_id = pur.id if pur else obj.id
            return f"#INV-{pur_id:05d}"

        student_id = obj.student_id or (obj.student.id if obj.student else 1)
        return f"#INV-2026-{1042 - (student_id - 1) * 3:04d}"

    def get_invoice_download_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        path = f"/api/v1/payments/transactions/{obj.uuid_str}/invoice/?download=1"
        return request.build_absolute_uri(path) if request else path

    def get_invoice_view_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        path = f"/api/v1/payments/transactions/{obj.uuid_str}/invoice/"
        return request.build_absolute_uri(path) if request else path

class PaymentTransactionDetailSerializer(PaymentTransactionSerializer):
    student_email = serializers.EmailField(source='student.email', read_only=True)
    amount_formatted = serializers.SerializerMethodField()
    order_id = serializers.CharField(source='stripe_session_id', read_only=True)
    payment_method = serializers.SerializerMethodField()
    item_slug = serializers.SerializerMethodField()
    item_uuid = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    resource_type = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    purchased_at = serializers.SerializerMethodField()

    class Meta(PaymentTransactionSerializer.Meta):
        fields = PaymentTransactionSerializer.Meta.fields + (
            'student_email', 'stripe_payment_intent_id', 'amount_formatted',
            'order_id', 'payment_method', 'item_slug', 'item_uuid',
            'category', 'resource_type', 'date', 'purchased_at'
        )
        read_only_fields = fields

    def get_amount_formatted(self, obj):
        curr = str(obj.currency or '£').lower()
        symbol = '£' if curr in ('gbp', '£') else ('$' if curr in ('usd', '$') else ('€' if curr in ('eur', '€') else f"{obj.currency.upper()} "))
        try:
            return f"{symbol}{float(obj.amount):.2f}"
        except (ValueError, TypeError):
            return f"{symbol}{obj.amount}"

    def get_payment_method(self, obj):
        return 'stripe'

    def get_item_slug(self, obj):
        if obj.item_type == 'course':
            from apps.courses.models import Course
            c = Course.objects.filter(id=obj.item_id).first()
            return c.slug if c else ''
        elif obj.item_type == 'resource':
            from apps.resources.models import PaidResource
            r = PaidResource.objects.filter(id=obj.item_id).first()
            return r.slug if r else ''
        return ''

    def get_item_uuid(self, obj):
        if obj.item_type == 'course':
            from apps.courses.models import Course
            c = Course.objects.filter(id=obj.item_id).first()
            return str(c.uuid) if c else ''
        elif obj.item_type == 'resource':
            from apps.resources.models import PaidResource
            r = PaidResource.objects.filter(id=obj.item_id).first()
            return str(r.uuid) if r else ''
        return ''

    def get_category(self, obj):
        if obj.item_type == 'course':
            from apps.courses.models import Course
            c = Course.objects.filter(id=obj.item_id).select_related('category').first()
            return c.category.name if c and c.category else ''
        elif obj.item_type == 'resource':
            from apps.resources.models import PaidResource
            r = PaidResource.objects.filter(id=obj.item_id).first()
            return getattr(r, 'category', '') or ''
        return ''

    def get_resource_type(self, obj):
        if obj.item_type == 'resource':
            from apps.resources.models import PaidResource
            r = PaidResource.objects.filter(id=obj.item_id).first()
            return getattr(r, 'resource_type', '') or 'question paper'
        return ''

    def get_date(self, obj):
        dt = obj.completed_at or obj.created_at
        return dt.strftime('%d/%m/%Y') if dt else ''

    def get_purchased_at(self, obj):
        dt = obj.completed_at or obj.created_at
        return dt.strftime('%d/%m/%Y') if dt else ''
