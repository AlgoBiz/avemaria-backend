from django.urls import path
from .views import (
    PaymentConfigView,
    CreateCheckoutSessionView,
    StripeWebhookView,
    VerifySessionView,
    StudentPaymentTransactionsView,
    StudentPaymentTransactionDetailView,
)

urlpatterns = [
    path('config/', PaymentConfigView.as_view(), name='payment-config'),
    path('create-checkout-session/', CreateCheckoutSessionView.as_view(), name='payment-create-checkout-session'),
    path('webhook/', StripeWebhookView.as_view(), name='payment-webhook'),
    path('verify-session/', VerifySessionView.as_view(), name='payment-verify-session'),
    path('transactions/', StudentPaymentTransactionsView.as_view(), name='payment-transactions'),
    path('transactions/<str:id>/', StudentPaymentTransactionDetailView.as_view(), name='payment-transaction-detail'),
    path('transaction/<str:id>/', StudentPaymentTransactionDetailView.as_view(), name='payment-transaction-detail-singular'),
    path('transaction/', StudentPaymentTransactionsView.as_view(), name='payment-transactions-singular'),
]
