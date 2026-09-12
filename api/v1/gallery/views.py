from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import models
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema

from apps.gallery.models import GalleryItem, GalleryCategory
from .serializers import GalleryItemSerializer, GalleryCategorySerializer


class GalleryCategoryViewSet(viewsets.ModelViewSet):
    queryset = GalleryCategory.objects.filter(is_deleted=False).order_by('id')
    serializer_class = GalleryCategorySerializer
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

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @extend_schema(
        summary="Create gallery category",
        description="Create gallery category endpoint at /api/v1/gallery/categories/create/",
        request=GalleryCategorySerializer,
        responses={201: GalleryCategorySerializer}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_category(self, request, *args, **kwargs):
        """Create gallery category endpoint at /api/v1/gallery/categories/create/"""
        return self.create(request, *args, **kwargs)


class GalleryItemViewSet(viewsets.ModelViewSet):
    queryset = GalleryItem.objects.filter(is_deleted=False)
    serializer_class = GalleryItemSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'caption', 'category', 'alt_text']
    ordering_fields = ['order', 'created_at', 'id']
    ordering = ['-created_at', '-id']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'stats', 'categories']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = GalleryItem.objects.filter(is_deleted=False)
        cat = self.request.query_params.get('category')
        if cat and cat.lower() != 'all':
            qs = qs.filter(
                models.Q(category__iexact=cat) |
                models.Q(category_slug__iexact=slugify(cat))
            )
        return qs.order_by('-created_at', '-id')

    def create(self, request, *args, **kwargs):
        # Support batch / multi-file upload from dropzone
        files = (
            request.FILES.getlist('images') or
            request.FILES.getlist('photos') or
            request.FILES.getlist('files') or
            (request.FILES.getlist('image') if len(request.FILES.getlist('image')) > 1 else [])
        )
        if files:
            title = request.data.get('title') or request.data.get('caption', '')
            caption = request.data.get('caption') or title
            cat_val = (
                request.data.get('default_category') or
                request.data.get('category') or
                request.data.get('category_name')
            )
            if not cat_val or not str(cat_val).strip():
                return Response(
                    {'category': ['Gallery category is required. Please select an existing category or add it first.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cleaned_cat = str(cat_val).strip()
            if cleaned_cat.isdigit():
                found_cat = GalleryCategory.objects.filter(id=int(cleaned_cat), is_deleted=False).first()
            else:
                found_cat = GalleryCategory.objects.filter(
                    is_deleted=False
                ).filter(
                    models.Q(name__iexact=cleaned_cat) | models.Q(slug__iexact=slugify(cleaned_cat))
                ).first()
            if not found_cat:
                return Response(
                    {'category': [f"Gallery category '{cleaned_cat}' does not exist. Please add the category first using the gallery categories API."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            category = found_cat.name
            category_slug = found_cat.slug
            alt_text = request.data.get('alt_text') or request.data.get('description', '')

            created_items = []
            for f in files:
                item_title = title or f.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
                item_caption = caption or item_title
                item = GalleryItem.objects.create(
                    title=item_title,
                    caption=item_caption,
                    category=category,
                    category_slug=slugify(category),
                    image=f,
                    alt_text=alt_text or item_title
                )
                created_items.append(item)
            return Response(
                GalleryItemSerializer(created_items, many=True, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Returns categories & photo counts for top counter: 5 categories · 5 photos"""
        total_cats = GalleryCategory.objects.filter(is_deleted=False).count()
        total_photos = GalleryItem.objects.filter(is_deleted=False).count()
        return Response({
            'total_categories': total_cats,
            'total_photos': total_photos,
            'summary_display': f"{total_cats} categories · {total_photos} photos"
        })

    @action(detail=False, methods=['post'], url_path='upload')
    def upload_single(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='upload-multiple')
    def upload_multiple(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    @extend_schema(
        summary="Create gallery item",
        description="Create gallery item endpoint at /api/v1/gallery/create/",
        request=GalleryItemSerializer,
        responses={201: GalleryItemSerializer}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_item(self, request, *args, **kwargs):
        """Create gallery item endpoint at /api/v1/gallery/create/"""
        return self.create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])
