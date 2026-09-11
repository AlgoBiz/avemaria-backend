from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.testimonials.models import Testimonial
from .serializers import TestimonialSerializer

class TestimonialViewSet(viewsets.ModelViewSet):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rating', 'is_featured', 'country']
    search_fields = ['candidate_name', 'quote', 'result_placement']
    ordering_fields = ['rating', 'created_at']
    ordering = ['-created_at', '-id']

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)
        if self.request.user and self.request.user.is_authenticated:
            return qs
        return qs.filter(is_featured=True, is_active=True)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['post'], url_path='create')
    def create_testimonial(self, request, *args, **kwargs):
        """Create testimonial endpoint at /api/v1/testimonials/create/"""
        return self.create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # Soft-delete so the testimonial immediately disappears from all lists
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])
