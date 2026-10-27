from django.db import models
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from apps.faculty.models import Faculty
from apps.courses.models import Course
from .serializers import FacultySerializer, FacultyListSerializer, FacultyStatsSerializer, FacultyMinimalSerializer


class FacultyViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Faculty & Mentors.
    Supports search, filtering, and image upload via multipart/form-data or json.
    """
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_published', 'is_featured', 'department', 'status']
    search_fields = ['name', 'title', 'qualification', 'department', 'bio']
    ordering_fields = ['created_at', 'display_order', 'name']
    ordering = ['-created_at', '-id']

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        base_qs = Faculty.objects.filter(is_deleted=False)
        total_faculties = base_qs.count()
        active_faculties = base_qs.filter(
            models.Q(status='active') | (models.Q(status='') & models.Q(is_active=True))
        ).count()
        total_covered_courses = Course.objects.filter(
            models.Q(faculty__isnull=False) | (models.Q(faculty_name__isnull=False) & ~models.Q(faculty_name='')),
            is_deleted=False
        ).values('id').distinct().count()

        stats_data = {
            'total_faculties': total_faculties,
            'active_faculties': active_faculties,
            'total_covered_courses': total_covered_courses,
        }

        if isinstance(response.data, dict):
            results = response.data.get('results')
            if results is not None:
                new_data = {}
                for k in ['count', 'next', 'previous']:
                    if k in response.data:
                        new_data[k] = response.data[k]
                new_data['stats'] = stats_data
                new_data['results'] = results
                for k, v in response.data.items():
                    if k not in new_data:
                        new_data[k] = v
                response.data = new_data
            else:
                response.data['stats'] = stats_data

        return response

    def get_serializer_class(self):
        if self.action == 'list':
            return FacultyListSerializer
        return FacultySerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)

        # Department filter (?department=Biomedical)
        department_param = self.request.query_params.get('department')
        if department_param and department_param.strip().lower() != 'all':
            qs = qs.filter(department__icontains=department_param.strip())

        # Status filter (?status=published / unpublished / featured)
        status_param = self.request.query_params.get('status')
        if status_param:
            status_param = status_param.strip().lower()
            if status_param == 'published':
                qs = qs.filter(is_published=True)
            elif status_param in ['unpublished', 'draft', 'drafts']:
                qs = qs.filter(is_published=False)
            elif status_param == 'featured':
                qs = qs.filter(is_featured=True)

        if self.request.user and self.request.user.is_authenticated:
            return qs
        return qs.filter(is_published=True)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'stats', 'minimal']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        from django.shortcuts import get_object_or_404
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

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @extend_schema(
        summary="Create faculty",
        description="Create faculty endpoint at /api/v1/faculty/create/ or /api/v1/faculty/",
        request=FacultySerializer,
        responses={201: FacultySerializer}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_faculty(self, request, *args, **kwargs):
        """Create faculty endpoint at /api/v1/faculty/create/"""
        return self.create(request, *args, **kwargs)

    @extend_schema(
        summary="Faculty dashboard metrics",
        description="Returns summary metrics for faculty management",
        responses={200: FacultyStatsSerializer}
    )
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Returns summary metrics for faculty management"""
        base_qs = Faculty.objects.filter(is_deleted=False)
        total_faculties = base_qs.count()
        active_faculties = base_qs.filter(
            models.Q(status='active') | (models.Q(status='') & models.Q(is_active=True))
        ).count()
        published = base_qs.filter(is_published=True).count()
        featured = base_qs.filter(is_featured=True).count()
        departments_count = base_qs.values('department').exclude(department='').distinct().count()

        total_covered_courses = Course.objects.filter(
            models.Q(faculty__isnull=False) | (models.Q(faculty_name__isnull=False) & ~models.Q(faculty_name='')),
            is_deleted=False
        ).values('id').distinct().count()

        stats_dict = {
            'total_faculties': total_faculties,
            'active_faculties': active_faculties,
            'total_covered_courses': total_covered_courses,
        }

        return Response({
            'total_faculties': total_faculties,
            'active_faculties': active_faculties,
            'total_covered_courses': total_covered_courses,
            'total': total_faculties,
            'published': published,
            'featured': featured,
            'departments_count': departments_count,
            'stats': stats_dict
        })

    @extend_schema(
        summary="List minimal faculty members without pagination",
        description="Returns an unpaginated minimal list of faculty members containing id, name, qualification, description, and image.",
        responses={200: FacultyMinimalSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='minimal', pagination_class=None)
    def minimal(self, request, *args, **kwargs):
        """Unpaginated minimal faculty list (id, name, qualification, description, image)."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = FacultyMinimalSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
