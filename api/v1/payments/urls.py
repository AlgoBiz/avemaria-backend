from django.urls import path
from .views import (
    PaymentConfigView,
    CreateCheckoutSessionView,
    StripeWebhookView,
    VerifySessionView,
    StudentPaymentTransactionsView,
    StudentPaymentTransactionDetailView,
    DownloadPaymentInvoicePdfView,
    DownloadPaymentInvoiceExcelView,
    ExportPaymentInvoicesExcelView,
)

urlpatterns = [
    path('config/', PaymentConfigView.as_view(), name='payment-config'),
    path('create-checkout-session/', CreateCheckoutSessionView.as_view(), name='payment-create-checkout-session'),
    path('webhook/', StripeWebhookView.as_view(), name='payment-webhook'),
    path('verify-session/', VerifySessionView.as_view(), name='payment-verify-session'),
    path('transactions/', StudentPaymentTransactionsView.as_view(), name='payment-transactions'),
    path('transactions/export-excel/', ExportPaymentInvoicesExcelView.as_view(), name='payment-transactions-export-excel'),
    path('transactions/export/', ExportPaymentInvoicesExcelView.as_view(), name='payment-transactions-export'),
    path('transactions/<str:id>/', StudentPaymentTransactionDetailView.as_view(), name='payment-transaction-detail'),
    path('transactions/<str:id>/invoice/', DownloadPaymentInvoicePdfView.as_view(), name='payment-transaction-invoice-pdf'),
    path('transactions/<str:id>/invoice-pdf/', DownloadPaymentInvoicePdfView.as_view(), name='payment-transaction-invoice-pdf-alt'),
    path('transactions/<str:id>/invoice-excel/', DownloadPaymentInvoiceExcelView.as_view(), name='payment-transaction-invoice-excel'),
    path('transactions/<str:id>/excel/', DownloadPaymentInvoiceExcelView.as_view(), name='payment-transaction-excel'),
    path('transaction/<str:id>/', StudentPaymentTransactionDetailView.as_view(), name='payment-transaction-detail-singular'),
    path('transaction/<str:id>/invoice/', DownloadPaymentInvoicePdfView.as_view(), name='payment-transaction-invoice-pdf-singular'),
    path('transaction/<str:id>/invoice-excel/', DownloadPaymentInvoiceExcelView.as_view(), name='payment-transaction-invoice-excel-singular'),
    path('transaction/', StudentPaymentTransactionsView.as_view(), name='payment-transactions-singular'),
    path('invoice/<str:id>/', DownloadPaymentInvoicePdfView.as_view(), name='payment-invoice-direct'),
    path('invoice/<str:id>/excel/', DownloadPaymentInvoiceExcelView.as_view(), name='payment-invoice-excel-direct'),
    path('export-excel/', ExportPaymentInvoicesExcelView.as_view(), name='payment-export-excel-direct'),
]
