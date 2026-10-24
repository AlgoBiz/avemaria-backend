import uuid
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import models
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.webinars.models import Webinar
from .serializers import (
    WebinarSerializer,
    WebinarListSerializer,
    WebinarStatsSerializer,
    WebinarToggleStatusResponseSerializer
)


class WebinarViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Webinars and Workshops.
    Supports GET (list & retrieve), POST (create), PUT (update), PATCH (partial update),
    and DELETE (soft delete).
    Handles both JSON and multipart/form-data with file uploads.
    """
    queryset = Webinar.objects.all()
    serializer_class = WebinarSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'status', 'platform']
    search_fields = ['title', 'summary_description', 'outline_agenda', 'platform', 'speaker__name']
    ordering_fields = ['scheduled_date', 'created_at', 'title', 'id']
    ordering = ['-scheduled_date', '-created_at', '-id']

    def get_serializer_class(self):
        if self.action == 'list':
            return WebinarListSerializer
        if self.action == 'stats':
            return WebinarStatsSerializer
        return WebinarSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'stats', 'upcoming']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        """
        Override list to include webinar/workshop counts in the response.
        The counts are computed from the base queryset (respecting auth visibility),
        so they remain stable regardless of search/type/status query params.
        """
        response = super().list(request, *args, **kwargs)

        # Base queryset for metric counts
        base_qs = Webinar.objects.filter(is_deleted=False)
        if not (request.user and request.user.is_authenticated):
            base_qs = base_qs.filter(status__in=[Webinar.STATUS_PUBLISHED, 'publish'])

        total_count = base_qs.count()
        webinars_count = base_qs.filter(type=Webinar.TYPE_WEBINAR).count()
        workshops_count = base_qs.filter(type=Webinar.TYPE_WORKSHOP).count()

        # Provide top-level keys and a nested counts object for frontend convenience
        response.data['total_count'] = total_count
        response.data['webinars_count'] = webinars_count
        response.data['workshops_count'] = workshops_count
        response.data['counts'] = {
            'total': total_count,
            'total_sessions': total_count,
            'webinars': webinars_count,
            'active_webinars': webinars_count,
            'workshops': workshops_count,
            'hands_on_workshops': workshops_count,
        }

        return response

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False).select_related('speaker')

        # Filter by type (?type=webinar / ?type=workshop)
        type_param = self.request.query_params.get('type')
        if type_param and type_param.strip().lower() != 'all':
            t = type_param.strip().lower()
            if t in ['webinar', 'webinars']:
                qs = qs.filter(type=Webinar.TYPE_WEBINAR)
            elif t in ['workshop', 'workshops']:
                qs = qs.filter(type=Webinar.TYPE_WORKSHOP)
            else:
                qs = qs.filter(type=t)

        # Filter by status (?status=publish / draft / published)
        status_param = self.request.query_params.get('status')
        if status_param and status_param.strip().lower() != 'all':
            s = status_param.strip().lower()
            if s in ['publish', 'published']:
                qs = qs.filter(status__in=[Webinar.STATUS_PUBLISHED, 'publish'])
            elif s in ['draft', 'unpublished']:
                qs = qs.filter(status=Webinar.STATUS_DRAFT)
            else:
                qs = qs.filter(status=s)
        elif not (self.request.user and self.request.user.is_authenticated):
            # By default unauthenticated public portal visitors only see published webinars/workshops
            qs = qs.filter(status__in=[Webinar.STATUS_PUBLISHED, 'publish'])

        # Filter by speaker (?speaker=1 or ?speaker=<uuid>)
        speaker_param = self.request.query_params.get('speaker')
        if speaker_param and speaker_param.strip().lower() != 'all':
            s_val = speaker_param.strip()
            if s_val.isdigit():
                qs = qs.filter(speaker_id=int(s_val))
            else:
                try:
                    s_uuid = uuid.UUID(s_val)
                    qs = qs.filter(speaker__uuid=s_uuid)
                except (ValueError, TypeError):
                    qs = qs.filter(speaker__name__icontains=s_val)

        # Filter upcoming vs past (?upcoming=true / ?past=true)
        today = timezone.localdate()
        upcoming_param = self.request.query_params.get('upcoming')
        if upcoming_param and upcoming_param.strip().lower() in ['true', '1', 'yes']:
            qs = qs.filter(scheduled_date__gte=today)

        past_param = self.request.query_params.get('past')
        if past_param and past_param.strip().lower() in ['true', '1', 'yes']:
            qs = qs.filter(scheduled_date__lt=today)

        return qs

    def get_object(self):
        lookup = self.kwargs.get('pk') or self.kwargs.get('slug')
        queryset = self.filter_queryset(self.get_queryset())
        if lookup is not None:
            l_str = str(lookup).strip()
            if l_str.isdigit():
                obj = queryset.filter(id=int(l_str)).first()
                if obj:
                    self.check_object_permissions(self.request, obj)
                    return obj

            try:
                u = uuid.UUID(l_str)
                obj = queryset.filter(uuid=u).first()
                if obj:
                    self.check_object_permissions(self.request, obj)
                    return obj
            except (ValueError, TypeError):
                pass

            # Slug lookup
            obj = queryset.filter(slug__iexact=l_str).first()
            if obj:
                self.check_object_permissions(self.request, obj)
                return obj

        return get_object_or_404(queryset, pk=lookup)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @extend_schema(
        summary="Create webinar or workshop",
        description="Create endpoint at /api/v1/webinars/create/ or /api/v1/webinars/",
        request=WebinarSerializer,
        responses={201: WebinarSerializer}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_webinar(self, request, *args, **kwargs):
        """Create webinar/workshop endpoint at /api/v1/webinars/create/"""
        return self.create(request, *args, **kwargs)

    @extend_schema(
        summary="Webinar & Workshop dashboard metrics",
        description="Returns counts for total, webinars, workshops, published, draft, and upcoming sessions",
        responses={200: WebinarStatsSerializer}
    )
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Returns summary metrics for webinars & workshops"""
        base_qs = Webinar.objects.filter(is_deleted=False)
        today = timezone.localdate()

        total = base_qs.count()
        webinars_count = base_qs.filter(type=Webinar.TYPE_WEBINAR).count()
        workshops_count = base_qs.filter(type=Webinar.TYPE_WORKSHOP).count()
        published_count = base_qs.filter(status__in=[Webinar.STATUS_PUBLISHED, 'publish']).count()
        draft_count = base_qs.filter(status=Webinar.STATUS_DRAFT).count()
        upcoming_count = base_qs.filter(scheduled_date__gte=today).count()

        data = {
            'total': total,
            'webinars_count': webinars_count,
            'workshops_count': workshops_count,
            'published_count': published_count,
            'draft_count': draft_count,
            'upcoming_count': upcoming_count,
            'summary_display': f"{webinars_count} webinars · {workshops_count} workshops ({published_count} published)"
        }
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="List upcoming webinars and workshops",
        description="Returns only upcoming published webinars and workshops scheduled on or after today",
        responses={200: WebinarListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming(self, request):
        """Returns upcoming published webinars and workshops"""
        today = timezone.localdate()
        qs = Webinar.objects.filter(
            is_deleted=False,
            status__in=[Webinar.STATUS_PUBLISHED, 'publish'],
            scheduled_date__gte=today
        ).select_related('speaker').order_by('scheduled_date', 'created_at')

        # Filter by type if provided
        type_param = request.query_params.get('type')
        if type_param and type_param.strip().lower() != 'all':
            qs = qs.filter(type__iexact=type_param.strip().lower())

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = WebinarListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = WebinarListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Toggle webinar/workshop status between publish and draft",
        responses={200: WebinarToggleStatusResponseSerializer}
    )
    @action(detail=True, methods=['post', 'patch'], url_path='toggle-status')
    def toggle_status(self, request, pk=None, slug=None):
        """Toggle publication status between publish and draft"""
        instance = self.get_object()
        new_status = Webinar.STATUS_DRAFT if instance.status in [Webinar.STATUS_PUBLISHED, 'publish'] else Webinar.STATUS_PUBLISHED
        instance.status = new_status
        instance.save(update_fields=['status', 'updated_at'])

        return Response({
            'success': True,
            'status': instance.status,
            'is_published': instance.is_published,
            'message': f"Status successfully updated to '{instance.status}'."
        }, status=status.HTTP_200_OK)
