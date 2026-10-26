from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.payments.models import PaymentTransaction


class PaymentConfigSerializer(serializers.Serializer):
    publishable_key = serializers.CharField(help_text="Stripe Publishable Key")
    currency = serializers.CharField(help_text="Default platform currency code e.g. gbp")


class CreateCheckoutSessionSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(
        choices=['course', 'resource'],
        help_text="Type of product being purchased ('course' or 'resource')"
    )
    item_id = serializers.CharField(
        help_text="ID or slug of the Course or PaidResource"
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


class CheckoutSessionResponseSerializer(serializers.Serializer):
    checkout_url = serializers.CharField(help_text="Stripe hosted checkout URL to redirect the user to")
    session_id = serializers.CharField(help_text="Stripe Checkout Session ID")
    publishable_key = serializers.CharField(help_text="Stripe publishable key")
    item_type = serializers.CharField()
    item_id = serializers.IntegerField()
    item_title = serializers.CharField()
    amount = serializers.FloatField()
    currency = serializers.CharField()


class VerifySessionSerializer(serializers.Serializer):
    session_id = serializers.CharField(help_text="Stripe Checkout Session ID to verify")


class VerifySessionResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="Payment status: paid, unpaid, or pending")
    item_type = serializers.CharField(allow_blank=True, required=False)
    item_id = serializers.IntegerField(allow_null=True, required=False)
    item_title = serializers.CharField(allow_blank=True, required=False)
    receipt_number = serializers.CharField(allow_blank=True, required=False)
    amount_paid = serializers.FloatField(required=False)
    currency = serializers.CharField(allow_blank=True, required=False)


class StripeWebhookPayloadSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, help_text="Stripe event ID")
    type = serializers.CharField(help_text="Stripe event type e.g. checkout.session.completed")
    data = serializers.DictField(help_text="Raw event object dictionary")



class PaymentTransactionSerializer(serializers.ModelSerializer):
    item_type_display = serializers.CharField(source='get_item_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    student_name = serializers.CharField(source='student.name', read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = (
            'id', 'uuid', 'item_type', 'item_type_display', 'item_id', 'item_title',
            'amount', 'currency', 'status', 'status_display', 'receipt_number',
            'stripe_session_id', 'completed_at', 'created_at', 'student_name'
        )
        read_only_fields = fields
