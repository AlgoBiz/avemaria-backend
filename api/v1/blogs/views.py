from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils.text import slugify
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.blogs.models import Blog, BlogCategory
from .serializers import (
    BlogListSerializer,
    BlogDetailSerializer,
    BlogCategorySerializer,
    BlogStatsSerializer,
    BlogCategoriesResponseSerializer,
    BlogTogglePublishedResponseSerializer,
)


class BlogCategoryViewSet(viewsets.ModelViewSet):
    queryset = BlogCategory.objects.filter(is_deleted=False).order_by('id')
    serializer_class = BlogCategorySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        lookup = self.kwargs.get('pk')
        queryset = self.filter_queryset(self.get_queryset())
        if str(lookup).isdigit():
            return get_object_or_404(queryset, pk=lookup)
        return get_object_or_404(queryset, slug__iexact=lookup)

    def list(self, request, *args, **kwargs):
        # Auto-seed default categories if empty
        if not BlogCategory.objects.filter(is_deleted=False).exists():
            default_categories = [
                'Exam Strategy', 'Career Pathways', 'Clinical Skills',
                'Licensing Updates', 'Study Advice'
            ]
            for name in default_categories:
                BlogCategory.objects.get_or_create(name=name)

        queryset = self.filter_queryset(self.get_queryset())
        categories_names = [c.name for c in queryset]
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            res = self.get_paginated_response(serializer.data)
            res.data['categories'] = categories_names
            return res
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'categories': categories_names,
            'results': serializer.data
        })

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @extend_schema(
        summary="Create blog category",
        description="Create blog category endpoint at /api/v1/blogs/categories/create/",
        request=BlogCategorySerializer,
        responses={201: BlogCategorySerializer}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_category(self, request, *args, **kwargs):
        """Create blog category endpoint at /api/v1/blogs/categories/create/"""
        return self.create(request, *args, **kwargs)



class BlogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Articles & Guidance Guides.
    Supports:
    - Listing articles with category and search filters
    - Creating and editing articles with content blocks & SEO tags
    - Summary counter (5 categories · 8 articles)
    - Dynamic categories management
    """
    queryset = Blog.objects.filter(is_deleted=False)
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'sub_heading', 'author_name', 'category']
    ordering_fields = ['publish_date', 'created_at', 'title', 'id']
    ordering = ['-created_at', '-id']

    def get_serializer_class(self):
        if self.action == 'list':
            return BlogListSerializer
        return BlogDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'stats', 'categories', 'category_detail']:
            if self.request.method == 'GET':
                return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = Blog.objects.filter(is_deleted=False)
        cat = self.request.query_params.get('category')
        if cat and cat.lower() != 'all':
            qs = qs.filter(
                Q(category__iexact=cat) |
                Q(category__iexact=cat.replace('-', ' ')) |
                Q(category__iexact=slugify(cat))
            )

        is_pub = self.request.query_params.get('is_published')
        if is_pub is not None:
            qs = qs.filter(is_published=str(is_pub).lower() in ['true', '1'])
        elif not (self.request.user and self.request.user.is_authenticated):
            qs = qs.filter(is_published=True)

        return qs.order_by('-created_at', '-id')

    def get_object(self):
        lookup = self.kwargs.get('pk')
        queryset = self.filter_queryset(self.get_queryset())
        if str(lookup).isdigit():
            return get_object_or_404(queryset, id=int(lookup))
        return get_object_or_404(queryset, slug=lookup)

    @extend_schema(
        summary="Blog statistics",
        description="Returns top counter matching: 5 categories · 8 articles",
        responses={200: BlogStatsSerializer}
    )
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Returns top counter matching: 5 categories · 8 articles"""
        total_cats = BlogCategory.objects.filter(is_deleted=False).count()
        total_articles = Blog.objects.filter(is_deleted=False).count()
        return Response({
            'total_categories': total_cats,
            'total_articles': total_articles,
            'summary_display': f"{total_cats} categories · {total_articles} articles"
        })

    @extend_schema(
        summary="Create blog article",
        description="Create article endpoint at /api/v1/blogs/create/",
        request=BlogDetailSerializer,
        responses={201: BlogDetailSerializer}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_blog(self, request, *args, **kwargs):
        """Create article endpoint at /api/v1/blogs/create/"""
        return self.create(request, *args, **kwargs)

    @extend_schema(
        methods=['GET'],
        summary="List blog categories",
        description="Returns list of categories and counts for filter pills",
        responses={200: BlogCategoriesResponseSerializer}
    )
    @extend_schema(
        methods=['POST'],
        summary="Create blog category",
        description="Creates a new Blog category from '+ Add Category' modal",
        request=BlogCategorySerializer,
        responses={201: BlogCategorySerializer}
    )
    @action(detail=False, methods=['get', 'post'], url_path='categories')
    def categories(self, request):
        """
        GET: Returns list of categories and counts for filter pills
        POST: Creates a new Blog category from '+ Add Category' modal
        """
        if request.method == 'POST':
            serializer = BlogCategorySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            cat = serializer.save()
            return Response(BlogCategorySerializer(cat).data, status=status.HTTP_201_CREATED)

        # Seed defaults if none exist
        if not BlogCategory.objects.filter(is_deleted=False).exists():
            default_categories = [
                'Exam Strategy', 'Career Pathways', 'Clinical Skills',
                'Licensing Updates', 'Study Advice'
            ]
            for name in default_categories:
                BlogCategory.objects.get_or_create(name=name)

        cat_objs = BlogCategory.objects.filter(is_deleted=False).order_by('id')
        all_count = Blog.objects.filter(is_deleted=False).count()

        return Response({
            'total_all': all_count,
            'categories': [c.name for c in cat_objs],
            'results': BlogCategorySerializer(cat_objs, many=True).data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        methods=['GET'],
        summary="Retrieve blog category",
        description="Retrieve a blog category by slug or ID",
        parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH, description="Blog category slug or ID")],
        responses={200: BlogCategorySerializer}
    )
    @extend_schema(
        methods=['PATCH', 'PUT'],
        summary="Update blog category",
        description="Update a blog category name and update linked blogs",
        parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH, description="Blog category slug or ID")],
        request=BlogCategorySerializer,
        responses={200: BlogCategorySerializer}
    )
    @extend_schema(
        methods=['DELETE'],
        summary="Delete blog category",
        description="Soft delete a blog category",
        parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH, description="Blog category slug or ID")],
        responses={204: None}
    )
    @action(detail=False, methods=['get', 'patch', 'put', 'delete'], url_path=r'categories/(?P<lookup>[^/.]+)')
    def category_detail(self, request, lookup=None):
        """Handles Edit and Delete for category pills at /api/v1/blogs/categories/<lookup>/"""
        if lookup.isdigit():
            category = get_object_or_404(BlogCategory, id=int(lookup), is_deleted=False)
        else:
            category = get_object_or_404(BlogCategory, slug__iexact=lookup, is_deleted=False)

        if request.method == 'GET':
            return Response(BlogCategorySerializer(category).data)

        elif request.method in ['PATCH', 'PUT']:
            old_name = category.name
            serializer = BlogCategorySerializer(category, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            updated_cat = serializer.save()

            new_name = updated_cat.name
            if old_name != new_name:
                Blog.objects.filter(category=old_name).update(category=new_name)

            return Response(BlogCategorySerializer(updated_cat).data)

        elif request.method == 'DELETE':
            category.is_deleted = True
            category.save(update_fields=['is_deleted'])
            return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Toggle published status",
        description="Toggle published status of a blog article",
        request=None,
        responses={200: BlogTogglePublishedResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='toggle-published')
    def toggle_published(self, request, pk=None):
        blog = self.get_object()
        blog.is_published = not blog.is_published
        blog.save()
        return Response({
            'success': True,
            'is_published': blog.is_published,
            'message': f"Blog '{blog.title}' {'published' if blog.is_published else 'unpublished'}."
        })

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])
