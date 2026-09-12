from django.db import models
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from apps.testimonials.models import Testimonial
from .serializers import TestimonialSerializer, TestimonialStatsSerializer

class TestimonialViewSet(viewsets.ModelViewSet):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rating', 'is_published', 'is_featured', 'country']
    search_fields = ['candidate_name', 'programme_name', 'result_placement', 'quote', 'country']
    ordering_fields = ['rating', 'created_at']
    ordering = ['-created_at', '-id']

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)

        # Handle filter tabs: Published / Unpublished / Student Submissions
        status_param = self.request.query_params.get('status')
        if status_param:
            status_param = status_param.strip().lower()
            if status_param == 'published':
                qs = qs.filter(is_published=True)
            elif status_param in ['unpublished', 'draft', 'drafts']:
                qs = qs.filter(is_published=False)
            elif status_param in ['student_submissions', 'student_submitted', 'submissions']:
                qs = qs.filter(is_student_submission=True)

        # Handle programme dropdown filter: ?programme=Gulf Licensing Preparation
        programme_param = self.request.query_params.get('programme') or self.request.query_params.get('programme_name')
        if programme_param and programme_param.strip().lower() != 'all':
            programme_param = programme_param.strip()
            qs = qs.filter(programme_name__icontains=programme_param)

        if self.request.user and self.request.user.is_authenticated:
            return qs
        return qs.filter(is_published=True, is_active=True)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'stats']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        summary="Testimonial dashboard metrics",
        description="Returns the top 4 summary metric cards for the admin testimonials dashboard",
        responses={200: TestimonialStatsSerializer}
    )
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Returns the top 4 summary metric cards for the admin testimonials dashboard"""
        total = Testimonial.objects.filter(is_deleted=False).count()
        published = Testimonial.objects.filter(is_published=True, is_deleted=False).count()
        unpublished = Testimonial.objects.filter(is_published=False, is_deleted=False).count()
        student_submitted = Testimonial.objects.filter(is_student_submission=True, is_deleted=False).count()

        return Response({
            'total_reviews': {
                'count': total,
                'label': 'Across all programmes'
            },
            'published': {
                'count': published,
                'label': 'Visible publicly on website'
            },
            'unpublished': {
                'count': unpublished,
                'label': 'Hidden from public view'
            },
            'student_submitted': {
                'count': student_submitted,
                'label': 'Direct student feedback'
            }
        })

    @extend_schema(
        summary="Toggle published status",
        description="Allows 1-click publishing or unpublishing directly from the card button",
        request=None,
        responses={200: TestimonialSerializer}
    )
    @action(detail=True, methods=['post'], url_path='toggle-publish')
    def toggle_publish(self, request, pk=None):
        """Allows 1-click publishing or unpublishing directly from the card button"""
        testimonial = self.get_object()
        testimonial.is_published = not testimonial.is_published
        testimonial.save(update_fields=['is_published'])
        return Response(self.get_serializer(testimonial).data)

    @extend_schema(
        summary="Create testimonial",
        description="Create testimonial endpoint at /api/v1/testimonials/create/",
        request=TestimonialSerializer,
        responses={201: TestimonialSerializer}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_testimonial(self, request, *args, **kwargs):
        """Create testimonial endpoint at /api/v1/testimonials/create/"""
        return self.create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # Soft-delete so the testimonial immediately disappears from all lists
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])
