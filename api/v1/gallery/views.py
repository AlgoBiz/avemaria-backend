from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.gallery.models import GalleryItem
from .serializers import GalleryItemSerializer

class GalleryItemViewSet(viewsets.ModelViewSet):
    queryset = GalleryItem.objects.filter(is_deleted=False)
    serializer_class = GalleryItemSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category']
    search_fields = ['caption', 'alt_text']
    ordering_fields = ['order', 'created_at']
    ordering = ['-created_at', '-id']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        files = (
            request.FILES.getlist('images') or
            request.FILES.getlist('files') or
            (request.FILES.getlist('image') if len(request.FILES.getlist('image')) > 1 else [])
        )
        if files:
            caption = request.data.get('caption') or request.data.get('title', '')
            category = request.data.get('category', 'Campus')
            alt_text = request.data.get('alt_text') or request.data.get('description', '')
            created_items = []
            for f in files:
                item = GalleryItem.objects.create(
                    image=f,
                    caption=caption or f.name,
                    category=category,
                    alt_text=alt_text
                )
                created_items.append(item)
            return Response(GalleryItemSerializer(created_items, many=True).data, status=status.HTTP_201_CREATED)

        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='create')
    def create_gallery_item(self, request, *args, **kwargs):
        """Create gallery photo endpoint at /api/v1/gallery/create/"""
        return self.create(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='upload-multiple')
    def upload_multiple(self, request, *args, **kwargs):
        """Upload multiple gallery images endpoint at /api/v1/gallery/upload-multiple/"""
        return self.create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # Soft-delete so the image immediately disappears from the gallery list
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])
