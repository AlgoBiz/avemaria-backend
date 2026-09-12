from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from apps.categories.models import Category
from .serializers import CategorySerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_deleted=False)
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['order', 'title', 'created_at']
    ordering = ['-created_at', '-id']

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

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

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @extend_schema(
        summary="Create category",
        description="Create category endpoint at /api/v1/courses/categories/create/",
        request=CategorySerializer,
        responses={201: CategorySerializer}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_category(self, request, *args, **kwargs):
        """Create category endpoint at /api/v1/courses/categories/create/"""
        return self.create(request, *args, **kwargs)
