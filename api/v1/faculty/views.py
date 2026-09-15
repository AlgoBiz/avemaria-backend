from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from apps.faculty.models import Faculty
from .serializers import FacultySerializer, FacultyListSerializer, FacultyStatsSerializer


class FacultyViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Faculty & Mentors.
    Supports search, filtering, and image upload via multipart/form-data or json.
    """
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_published', 'is_featured', 'department']
    search_fields = ['name', 'title', 'qualification', 'department', 'bio']
    ordering_fields = ['display_order', 'name', 'created_at']
    ordering = ['display_order', '-created_at', '-id']

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
        if self.action in ['list', 'retrieve', 'stats']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

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
        total = base_qs.count()
        published = base_qs.filter(is_published=True).count()
        featured = base_qs.filter(is_featured=True).count()
        departments_count = base_qs.values('department').exclude(department='').distinct().count()

        return Response({
            'total': total,
            'published': published,
            'featured': featured,
            'departments_count': departments_count
        })
