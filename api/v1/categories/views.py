from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from apps.categories.models import Category
from .serializers import (
    CategorySerializer,
    CategoryListSerializer,
    CategoryCreateSerializer,
    CategoryMinimalSerializer,
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_deleted=False)
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'minimal':
            return CategoryMinimalSerializer
        if self.action in ['list', 'all_categories']:
            return CategoryListSerializer
        if self.action in ['create', 'create_category']:
            return CategoryCreateSerializer
        return CategorySerializer
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
        if lookup is not None:
            l_str = str(lookup).strip()
            if l_str.isdigit():
                return get_object_or_404(queryset, id=int(l_str))
            import uuid
            try:
                u = uuid.UUID(l_str)
                obj = queryset.filter(uuid=u).first()
                if obj:
                    return obj
            except (ValueError, TypeError):
                pass
        return get_object_or_404(queryset, slug=lookup)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'all_categories', 'minimal']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_destroy(self, instance):
        if instance.cover_image:
            instance.cover_image.delete(save=False)
        instance.delete()

    @extend_schema(
        summary="Create category",
        description="Create category endpoint at /api/v1/courses/categories/create/",
        request=CategoryCreateSerializer,
        responses={201: CategoryCreateSerializer}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_category(self, request, *args, **kwargs):
        """Create category endpoint at /api/v1/courses/categories/create/"""
        return self.create(request, *args, **kwargs)

    @extend_schema(
        summary="List all categories without pagination",
        description="Returns an unpaginated flat list of all active course categories for navigation, selectors and cards.",
        responses={200: CategoryListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='all', pagination_class=None)
    def all_categories(self, request, *args, **kwargs):
        """Unpaginated list of all active categories."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = CategoryListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="List minimal course categories without pagination",
        description="Returns an unpaginated minimal list of course categories (id, name, title, slug) for selectors and dropdowns.",
        responses={200: CategoryMinimalSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='minimal', pagination_class=None)
    def minimal(self, request, *args, **kwargs):
        """Unpaginated minimal list of active course categories."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = CategoryMinimalSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
