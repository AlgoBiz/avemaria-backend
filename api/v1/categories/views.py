from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.db import models
from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse
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
        # 1. Permanently purge any previously soft-deleted categories from DB
        Category.objects.filter(is_deleted=True).delete()
        # 2. Automatically sync any active category whose slug is out-of-sync with its title
        try:
            for cat in Category.objects.filter(is_deleted=False):
                expected_base = slugify(cat.title) or 'category'
                if cat.slug != expected_base and not cat.slug.startswith(f"{expected_base}-"):
                    new_unique = expected_base
                    c = 1
                    while Category.objects.filter(slug=new_unique).exclude(pk=cat.pk).exists():
                        new_unique = f"{expected_base}-{c}"
                        c += 1
                    cat.slug = new_unique
                    cat.save(update_fields=['slug'])
        except Exception:
            pass
        return super().get_queryset().filter(is_deleted=False)

    def get_object(self):
        lookup = (
            self.kwargs.get('slug') or
            self.kwargs.get('pk') or
            (self.request.query_params.get('id') if hasattr(self, 'request') and self.request else None) or
            (self.request.query_params.get('slug') if hasattr(self, 'request') and self.request else None) or
            (self.request.query_params.get('pk') if hasattr(self, 'request') and self.request else None) or
            (self.request.query_params.get('uuid') if hasattr(self, 'request') and self.request else None) or
            (self.request.query_params.get('title') if hasattr(self, 'request') and self.request else None)
        )
        queryset = Category.objects.all()
        if lookup is not None:
            l_str = str(lookup).strip()
            if l_str.isdigit():
                obj = queryset.filter(id=int(l_str)).first()
                if obj:
                    return obj
            import uuid
            try:
                u = uuid.UUID(l_str)
                obj = queryset.filter(uuid=u).first()
                if obj:
                    return obj
            except (ValueError, TypeError):
                pass
            slug_q = models.Q(slug__iexact=l_str) | models.Q(title__iexact=l_str)
            slugified = slugify(l_str)
            if slugified:
                slug_q |= models.Q(slug=slugified)
            obj = queryset.filter(slug_q).first()
            if obj:
                return obj
        return get_object_or_404(queryset, slug=lookup)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'all_categories', 'minimal']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        summary="Delete course category permanently (hard delete)",
        description="Permanently delete a course category from the database.",
        responses={200: OpenApiResponse(description="Category permanently deleted")}
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"status": "success", "message": "Course category permanently deleted successfully."},
            status=status.HTTP_200_OK
        )

    def perform_destroy(self, instance):
        if instance.cover_image:
            try:
                instance.cover_image.delete(save=False)
            except Exception:
                pass
        # Hard delete permanently from the database
        instance.delete()

    @extend_schema(
        summary="Delete category by ID, UUID, or slug",
        description="Permanently delete course category via query parameter or body (?id=<id> or ?slug=<slug>).",
        responses={200: OpenApiResponse(description="Category permanently deleted")}
    )
    @action(detail=False, methods=['delete', 'post'], url_path='delete')
    def delete_category(self, request, *args, **kwargs):
        lookup = (
            request.query_params.get('id') or
            request.query_params.get('slug') or
            request.query_params.get('pk') or
            request.query_params.get('uuid') or
            request.query_params.get('title') or
            (request.data.get('id') if isinstance(request.data, dict) else None) or
            (request.data.get('slug') if isinstance(request.data, dict) else None) or
            (request.data.get('pk') if isinstance(request.data, dict) else None) or
            (request.data.get('uuid') if isinstance(request.data, dict) else None) or
            (request.data.get('title') if isinstance(request.data, dict) else None)
        )
        if not lookup:
            return Response(
                {"detail": "Category id, uuid, or slug is required to delete."},
                status=status.HTTP_400_BAD_REQUEST
            )
        self.kwargs['slug'] = str(lookup)
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"status": "success", "message": "Course category permanently deleted successfully."},
            status=status.HTTP_200_OK
        )

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
