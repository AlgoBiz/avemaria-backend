from django.contrib import admin
from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'student', 'item_type', 'item_title',
        'amount', 'currency', 'status', 'stripe_session_id', 'created_at'
    )
    list_filter = ('item_type', 'status', 'currency', 'created_at')
    search_fields = (
        'student__name', 'student__email', 'item_title',
        'stripe_session_id', 'stripe_payment_intent_id', 'receipt_number'
    )
    readonly_fields = (
        'uuid', 'created_at', 'updated_at', 'completed_at',
        'stripe_session_id', 'stripe_payment_intent_id'
    )
