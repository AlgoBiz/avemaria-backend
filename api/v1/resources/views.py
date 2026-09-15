from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from apps.resources.models import PaidResource, ResourcePDF, ResourceCategory
from .serializers import (
    PaidResourceSerializer,
    ResourceListSerializer,
    ResourcePDFSerializer,
    ResourcePDFUploadSerializer,
    ResourceCategorySerializer,
    ResourcePurchaseSerializer,
    StudentPurchaseHistorySerializer,
    StudentPaymentDetailItemSerializer,
    StudentReceiptSerializer,
    DeletePdfResponseSerializer,
    PurchasedResourcesResponseSerializer,
    PurchaseHistoryResponseSerializer,
    PaymentDetailsResponseSerializer,
    ReceiptsListResponseSerializer,
)

class PaidResourceViewSet(viewsets.ModelViewSet):
    queryset = PaidResource.objects.prefetch_related('pdf_files').all()
    serializer_class = PaidResourceSerializer
    lookup_field = 'slug'
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['title', 'description', 'course_name', 'category']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at', '-id']

    def get_serializer_class(self):
        if self.action == 'list':
            return ResourceListSerializer
        return PaidResourceSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)
        category_param = self.request.query_params.get('category')
        if category_param and category_param.strip().lower() != 'all':
            category_param = category_param.strip()
            slug_variant = category_param.replace('-', ' ')
            qs = qs.filter(models.Q(category__iexact=category_param) | models.Q(category__iexact=slug_variant))

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
        if self.action in ['categories', 'category_detail'] and self.request.method == 'GET':
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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        resource = serializer.save()

        # Handle any PDF files uploaded during update
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

        return Response(self.get_serializer(resource).data)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @extend_schema(
        summary="Create resource",
        description="Create resource endpoint at /api/v1/resources/create/",
        request=PaidResourceSerializer,
        responses={201: PaidResourceSerializer}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_resource(self, request, *args, **kwargs):
        """Create resource endpoint at /api/v1/resources/create/"""
        return self.create(request, *args, **kwargs)

    @extend_schema(
        methods=['GET'],
        summary="List resource categories",
        description="List all resource categories with counts",
        responses={200: ResourceCategorySerializer(many=True)}
    )
    @extend_schema(
        methods=['POST'],
        summary="Create resource category",
        description="Create new resource category (Admin)",
        request=ResourceCategorySerializer,
        responses={201: ResourceCategorySerializer}
    )
    @action(detail=False, methods=['get', 'post'], url_path='categories')
    def categories(self, request):
        """
        GET: List all resource categories with counts
        POST: Create new resource category (Admin)
        """
        if request.method == 'POST':
            serializer = ResourceCategorySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            category = serializer.save()
            return Response(ResourceCategorySerializer(category).data, status=status.HTTP_201_CREATED)

        # GET: Seed default categories if none exist, then return all non-deleted
        existing = ResourceCategory.objects.filter(is_deleted=False)
        if not existing.exists():
            for name in ['Question Papers', 'Notes', 'Video Pack', 'Exam Blueprint', 'Mock Test Set']:
                ResourceCategory.objects.get_or_create(name=name)

        categories = ResourceCategory.objects.filter(is_deleted=False)
        return Response(ResourceCategorySerializer(categories, many=True).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create resource category",
        description="Create resource category endpoint at /api/v1/resources/categories/create/",
        request=ResourceCategorySerializer,
        responses={201: ResourceCategorySerializer}
    )
    @action(detail=False, methods=['post'], url_path='categories/create')
    def create_resource_category(self, request, *args, **kwargs):
        """Create resource category endpoint at /api/v1/resources/categories/create/"""
        serializer = ResourceCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(ResourceCategorySerializer(category).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        methods=['GET'],
        summary="Retrieve resource category",
        description="Retrieve a specific resource category by ID or slug",
        parameters=[OpenApiParameter("cat_lookup", str, OpenApiParameter.PATH, description="Resource category slug or ID")],
        responses={200: ResourceCategorySerializer}
    )
    @extend_schema(
        methods=['PATCH', 'PUT'],
        summary="Update resource category",
        description="Update a specific resource category name or details",
        parameters=[OpenApiParameter("cat_lookup", str, OpenApiParameter.PATH, description="Resource category slug or ID")],
        request=ResourceCategorySerializer,
        responses={200: ResourceCategorySerializer}
    )
    @extend_schema(
        methods=['DELETE'],
        summary="Delete resource category",
        description="Soft-delete a specific resource category",
        parameters=[OpenApiParameter("cat_lookup", str, OpenApiParameter.PATH, description="Resource category slug or ID")],
        responses={204: None}
    )
    @action(detail=False, methods=['get', 'patch', 'put', 'delete'], url_path=r'categories/(?P<cat_lookup>(?!create$)[^/.]+)')
    def category_detail(self, request, cat_lookup=None):
        """
        GET / PATCH / PUT / DELETE a specific resource category
        Allows editing category name (pencil icon) or deleting category (trash icon)
        """
        if cat_lookup == 'create' and request.method == 'POST':
            return self.create_resource_category(request)

        if cat_lookup and cat_lookup.isdigit():
            category = get_object_or_404(ResourceCategory, id=int(cat_lookup), is_deleted=False)
        else:
            category = get_object_or_404(ResourceCategory, slug=cat_lookup, is_deleted=False)

        if request.method == 'GET':
            return Response(ResourceCategorySerializer(category).data)

        if request.method in ['PATCH', 'PUT']:
            serializer = ResourceCategorySerializer(category, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            category = serializer.save()
            return Response(ResourceCategorySerializer(category).data)

        if request.method == 'DELETE':
            category.is_deleted = True
            category.save(update_fields=['is_deleted'])
            return Response({'message': 'Resource category deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


    @extend_schema(
        summary="Upload PDF to resource",
        description="Upload a new PDF file attachment to this resource",
        request=ResourcePDFUploadSerializer,
        responses={201: ResourcePDFSerializer}
    )
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

    @extend_schema(
        summary="Delete PDF from resource",
        description="Delete a PDF attachment from this resource",
        parameters=[OpenApiParameter("pdf_id", str, OpenApiParameter.PATH, description="ID of PDF attachment")],
        responses={200: DeletePdfResponseSerializer}
    )
    @action(detail=True, methods=['delete'], url_path='pdf/(?P<pdf_id>[^/.]+)', permission_classes=[permissions.IsAuthenticated])
    def delete_pdf(self, request, slug=None, pdf_id=None):
        resource = self.get_object()
        try:
            pdf = resource.pdf_files.get(id=pdf_id)
            pdf.delete()
            return Response({'message': 'PDF deleted successfully.'}, status=status.HTTP_200_OK)
        except ResourcePDF.DoesNotExist:
            return Response({'error': 'PDF not found.'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        summary="List student purchased resources",
        description="Endpoint at /api/v1/resources/purchased/ for student's purchased resources.",
        responses={200: PurchasedResourcesResponseSerializer}
    )
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

    @extend_schema(
        summary="List student purchase history",
        description="Endpoint at /api/v1/resources/purchase-history/ matching the table columns.",
        responses={200: PurchaseHistoryResponseSerializer}
    )
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

    @extend_schema(
        summary="Retrieve student payment details",
        description="Endpoint at /api/v1/resources/payment-details/ with summary and payment lines.",
        responses={200: PaymentDetailsResponseSerializer}
    )
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

    @extend_schema(
        summary="List student receipts",
        description="Endpoint at /api/v1/resources/receipts/ matching the receipts list interface.",
        responses={200: ReceiptsListResponseSerializer}
    )
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




