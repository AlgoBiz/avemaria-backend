from django.urls import path
from .views import (
    PaymentConfigView,
    CreateCheckoutSessionView,
    StripeWebhookView,
    VerifySessionView,
    StudentPaymentTransactionsView,
)

urlpatterns = [
    path('config/', PaymentConfigView.as_view(), name='payment-config'),
    path('create-checkout-session/', CreateCheckoutSessionView.as_view(), name='payment-create-checkout-session'),
    path('webhook/', StripeWebhookView.as_view(), name='payment-webhook'),
    path('verify-session/', VerifySessionView.as_view(), name='payment-verify-session'),
    path('transactions/', StudentPaymentTransactionsView.as_view(), name='payment-transactions'),
]
