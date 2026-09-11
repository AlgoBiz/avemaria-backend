from django.shortcuts import get_object_or_404
from django.db.models import Count
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.blogs.models import Blog
from .serializers import BlogListSerializer, BlogDetailSerializer

class BlogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Blogs & Articles.
    Provides endpoints for:
    - Listing blogs with category/search filters
    - Viewing detail by numeric ID or slug
    - Publishing/Creating new blogs
    - Listing active categories for UI filter pills
    """
    queryset = Blog.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_published']
    search_fields = ['title', 'sub_heading', 'author_name']
    ordering_fields = ['publish_date', 'created_at', 'title']
    ordering = ['-created_at', '-id']


    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)
        if self.request.user and self.request.user.is_authenticated:
            return qs
        return qs.filter(is_published=True, is_active=True)

    def get_object(self):
        lookup = self.kwargs.get('pk')
        queryset = self.filter_queryset(self.get_queryset())
        if lookup.isdigit():
            return get_object_or_404(queryset, id=int(lookup))
        return get_object_or_404(queryset, slug=lookup)

    def get_serializer_class(self):
        if self.action == 'list':
            return BlogListSerializer
        return BlogDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'categories']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['post'], url_path='create')
    def create_blog(self, request, *args, **kwargs):
        """Create blog endpoint at /api/v1/blogs/create/"""
        return self.create(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='categories')
    def categories(self, request):
        """
        Returns list of categories and counts for the filter pills in the admin UI:
        e.g., All, Exam Strategy, Career Pathways, Clinical Skills, Licensing Updates, Study Advice
        """
        all_count = Blog.objects.filter(is_deleted=False).count()
        cat_counts = (
            Blog.objects.filter(is_deleted=False)
            .values('category')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        default_categories = [
            'All', 'Exam Strategy', 'Career Pathways', 'Clinical Skills',
            'Licensing Updates', 'Study Advice', 'Licensing', 'Haematology',
            'Quality', 'Careers', 'Postgraduate'
        ]

        return Response({
            'total_all': all_count,
            'categories': default_categories,
            'counts': list(cat_counts)
        }, status=status.HTTP_200_OK)

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

