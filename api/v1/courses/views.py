from django.db import models
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from apps.courses.models import Course
from .serializers import CourseListSerializer, CourseDetailSerializer, CourseWriteSerializer, FacultyListResponseSerializer

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related('category').all()
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'category__title', 'level', 'learning_mode', 'is_published', 'is_featured']
    search_fields = ['title', 'summary', 'overview_description', 'faculty_name', 'faculty_title', 'faculty_qualification', 'meta_description']
    ordering_fields = ['fee', 'rating', 'created_at', 'title']
    ordering = ['-created_at', '-id']

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)
        category_param = self.request.query_params.get('category')
        if category_param and category_param.strip().lower() != 'all':
            category_param = category_param.strip()
            if category_param.isdigit():
                qs = qs.filter(category_id=int(category_param))
            else:
                qs = qs.filter(models.Q(category__slug__iexact=category_param) | models.Q(category__title__iexact=category_param))

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
        if self.action in ['list', 'retrieve', 'list_faculties']:
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

    @extend_schema(
        summary="Create course",
        description="Create course endpoint at /api/v1/courses/create/",
        request=CourseWriteSerializer,
        responses={201: CourseDetailSerializer}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_course(self, request, *args, **kwargs):
        """Create course endpoint at /api/v1/courses/create/"""
        return self.create(request, *args, **kwargs)

    @extend_schema(
        summary="List faculties",
        description="Returns distinct faculty profiles across all published courses for 'Select Existing Faculty' modal",
        responses={200: FacultyListResponseSerializer}
    )
    @action(detail=False, methods=['get'], url_path='faculties')
    def list_faculties(self, request):
        """Returns distinct faculty profiles across all published courses for 'Select Existing Faculty' modal"""
        from apps.faculty.models import Faculty
        faculty_qs = Faculty.objects.filter(is_deleted=False, is_published=True).order_by('-created_at', '-id')
        seen = set()
        faculties = []

        for f in faculty_qs:
            name = (f.name or '').strip()
            if name and name.lower() not in seen:
                seen.add(name.lower())
                faculties.append({
                    'faculty_name': name,
                    'faculty_title': f.title or '',
                    'faculty_qualification': f.qualification or f.title or '',
                    'faculty_experience': f.experience or '',
                    'faculty_bio': f.bio or '',
                    'faculty_display': f.faculty_display,
                    'faculty_image': f.image.url if f.image else None
                })

        courses = Course.objects.filter(is_deleted=False).exclude(faculty_name='').exclude(faculty_name__isnull=True).order_by('-created_at', '-id')
        for c in courses:
            name = (c.faculty_name or '').strip()
            if name and name.lower() not in seen:
                seen.add(name.lower())
                faculties.append({
                    'faculty_name': name,
                    'faculty_title': c.faculty_title or '',
                    'faculty_qualification': c.faculty_qualification or c.faculty_title or '',
                    'faculty_experience': c.faculty_experience or '',
                    'faculty_bio': c.faculty_bio or '',
                    'faculty_display': f"{name} ({c.faculty_qualification or c.faculty_title})" if (c.faculty_qualification or c.faculty_title) else name,
                    'faculty_image': c.faculty_image.url if c.faculty_image else None
                })
        return Response({'count': len(faculties), 'results': faculties})
