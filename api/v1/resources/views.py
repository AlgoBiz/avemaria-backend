from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from apps.resources.models import PaidResource, ResourcePDF
from .serializers import PaidResourceSerializer, ResourcePDFSerializer, ResourcePDFUploadSerializer

class PaidResourceViewSet(viewsets.ModelViewSet):
    queryset = PaidResource.objects.prefetch_related('pdf_files').all()
    serializer_class = PaidResourceSerializer
    lookup_field = 'slug'
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at', '-id']

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)
        if self.request.user and self.request.user.is_authenticated:
            return qs
        return qs.filter(is_active=True)

    def get_object(self):
        lookup = self.kwargs.get('slug') or self.kwargs.get('pk')
        queryset = self.filter_queryset(self.get_queryset())
        if lookup is not None and str(lookup).isdigit():
            return get_object_or_404(queryset, id=int(lookup))
        return get_object_or_404(queryset, slug=lookup)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resource = serializer.save()

        # Handle any initial PDF files uploaded with the resource
        files = (
            request.FILES.getlist('pdf_files') or
            request.FILES.getlist('files') or
            request.FILES.getlist('file') or
            request.FILES.getlist('pdfs')
        )
        for f in files:
            size_mb = f.size / (1024 * 1024)
            file_size = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{f.size / 1024:.0f} KB"
            ResourcePDF.objects.create(
                resource=resource,
                file=f,
                title=f.name,
                file_size=file_size
            )

        headers = self.get_success_headers(serializer.data)
        response_serializer = self.get_serializer(resource)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @action(detail=False, methods=['post'], url_path='create')
    def create_resource(self, request, *args, **kwargs):
        """Create resource endpoint at /api/v1/resources/create/"""
        return self.create(request, *args, **kwargs)


    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser], permission_classes=[permissions.IsAuthenticated])
    def upload_pdf(self, request, slug=None):
        resource = self.get_object()
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        size_mb = file_obj.size / (1024 * 1024)
        file_size = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{file_obj.size / 1024:.0f} KB"

        pdf = ResourcePDF.objects.create(
            resource=resource,
            file=file_obj,
            title=request.data.get('title', file_obj.name),
            file_size=file_size
        )
        return Response(ResourcePDFSerializer(pdf).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='pdf/(?P<pdf_id>[^/.]+)', permission_classes=[permissions.IsAuthenticated])
    def delete_pdf(self, request, slug=None, pdf_id=None):
        resource = self.get_object()
        try:
            pdf = resource.pdf_files.get(id=pdf_id)
            pdf.delete()
            return Response({'message': 'PDF deleted successfully.'}, status=status.HTTP_200_OK)
        except ResourcePDF.DoesNotExist:
            return Response({'error': 'PDF not found.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='purchased', permission_classes=[permissions.IsAuthenticated])
    def purchased_resources(self, request):
        """Endpoint at /api/v1/resources/purchased/ for student's purchased resources."""
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)

        from apps.resources.models import ResourcePurchase
        from .serializers import ResourcePurchaseSerializer
        purchases = ResourcePurchase.objects.filter(
            student=student,
            is_deleted=False
        ).select_related('resource').prefetch_related('resource__pdf_files').order_by('-purchased_at')

        serializer = ResourcePurchaseSerializer(purchases, many=True, context={'request': request})
        return Response({
            "count": purchases.count(),
            "results": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='purchase-history', permission_classes=[permissions.IsAuthenticated])
    def purchase_history(self, request):
        """Endpoint at /api/v1/resources/purchase-history/ matching the table columns."""
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)

        from apps.resources.models import ResourcePurchase
        from .serializers import StudentPurchaseHistorySerializer
        purchases = list(ResourcePurchase.objects.filter(
            student=student,
            is_deleted=False
        ).select_related('resource').order_by('-purchased_at'))

        for idx, item in enumerate(purchases, start=1):
            item.sl_no = idx

        serializer = StudentPurchaseHistorySerializer(purchases, many=True, context={'request': request})
        return Response({
            "count": len(purchases),
            "results": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='payment-details', permission_classes=[permissions.IsAuthenticated])
    def payment_details(self, request):
        """Endpoint at /api/v1/resources/payment-details/ with summary and payment lines."""
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({
                "summary": {
                    "total_spent": "0.00",
                    "total_spent_formatted": "£0.00",
                    "currency": "£",
                    "completed_payments": 0,
                    "pending_payments": 0,
                    "total_transactions": 0
                },
                "payment_methods_notice": {
                    "title": "Payment methods",
                    "note": "Card details are never stored on our servers. Every payment is taken on our payment provider’s secure checkout, and your saved cards are managed there."
                },
                "results": []
            }, status=status.HTTP_200_OK)

        from django.db.models import Sum
        from apps.resources.models import ResourcePurchase
        from .serializers import StudentPaymentDetailItemSerializer

        purchases = ResourcePurchase.objects.filter(
            student=student,
            is_deleted=False
        ).select_related('resource').order_by('-purchased_at')

        paid_purchases = purchases.filter(payment_status='paid')
        completed_count = paid_purchases.count()
        pending_count = purchases.filter(payment_status='pending').count()

        total_val = paid_purchases.aggregate(total=Sum('amount_paid'))['total'] or 0.00
        currency = '£'
        first_p = purchases.first()
        if first_p and first_p.currency:
            currency = first_p.currency

        serializer = StudentPaymentDetailItemSerializer(purchases, many=True, context={'request': request})

        return Response({
            "summary": {
                "total_spent": f"{total_val:.2f}",
                "total_spent_formatted": f"{currency}{total_val:.2f}",
                "currency": currency,
                "completed_payments": completed_count,
                "pending_payments": pending_count,
                "total_transactions": purchases.count()
            },
            "payment_methods_notice": {
                "title": "Payment methods",
                "note": "Card details are never stored on our servers. Every payment is taken on our payment provider’s secure checkout, and your saved cards are managed there."
            },
            "results": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='receipts', permission_classes=[permissions.IsAuthenticated])
    def receipts(self, request):
        """Endpoint at /api/v1/resources/receipts/ matching the receipts list interface."""
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)

        from apps.resources.models import ResourcePurchase
        from .serializers import StudentReceiptSerializer

        purchases = ResourcePurchase.objects.filter(
            student=student,
            is_deleted=False
        ).select_related('resource').prefetch_related('resource__pdf_files').order_by('-purchased_at')

        serializer = StudentReceiptSerializer(purchases, many=True, context={'request': request})
        return Response({
            "count": purchases.count(),
            "results": serializer.data
        }, status=status.HTTP_200_OK)




