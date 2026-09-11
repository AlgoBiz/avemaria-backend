from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from apps.courses.models import Course
from .serializers import CourseListSerializer, CourseDetailSerializer, CourseWriteSerializer

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related('category').all()
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'level', 'is_published', 'is_featured']
    search_fields = ['title', 'summary', 'faculty_name', 'meta_description']
    ordering_fields = ['fee', 'rating', 'created_at', 'title']
    ordering = ['-created_at', '-id']


    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)
        if self.request.user and self.request.user.is_authenticated:
            return qs
        # Public users see active, published courses only
        return qs.filter(is_published=True, is_active=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        elif self.action in ['create', 'create_course', 'update', 'partial_update']:
            return CourseWriteSerializer
        return CourseDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        from django.shortcuts import get_object_or_404
        lookup = self.kwargs.get('slug') or self.kwargs.get('pk')
        queryset = self.filter_queryset(self.get_queryset())
        if lookup is not None and str(lookup).isdigit():
            return get_object_or_404(queryset, id=int(lookup))
        return get_object_or_404(queryset, slug=lookup)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @action(detail=False, methods=['post'], url_path='create')
    def create_course(self, request, *args, **kwargs):
        """Create course endpoint at /api/v1/courses/create/"""
        return self.create(request, *args, **kwargs)
