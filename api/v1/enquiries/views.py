import csv
from django.http import HttpResponse
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from apps.enquiries.models import Enquiry
from .serializers import (
    EnquiryCreateSerializer,
    EnquiryAdminSerializer,
    EnquiryStatusUpdateSerializer,
    EnquiryStatsResponseSerializer,
    EnquiryReplySerializer,
    EnquiryReplyResponseSerializer,
    EnquiryStatusChangeResponseSerializer,
)

class EnquiryViewSet(viewsets.ModelViewSet):
    queryset = Enquiry.objects.filter(is_deleted=False)
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['candidate_name', 'email', 'phone', 'topic', 'message']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at', '-id']

    def get_serializer_class(self):
        if self.action in ['create', 'create_enquiry', 'contact_enquiry', 'submit_enquiry']:
            return EnquiryCreateSerializer
        return EnquiryAdminSerializer

    def get_permissions(self):
        if self.action in ['create', 'create_enquiry', 'contact_enquiry', 'submit_enquiry', 'export_csv', 'export_csv_hyphen', 'export_leads']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = Enquiry.objects.filter(is_deleted=False)
        status_param = self.request.query_params.get('status')
        if status_param and status_param.lower() != 'all':
            s_clean = status_param.strip().lower()
            if s_clean in ['new', 'new lead', 'new-lead', 'new_lead']:
                qs = qs.filter(status='new')
            elif s_clean in ['contacted']:
                qs = qs.filter(status='contacted')
            elif s_clean in ['resolved']:
                qs = qs.filter(status='resolved')
            else:
                qs = qs.filter(status=status_param)
        return qs.order_by('-created_at', '-id')

    @extend_schema(
        summary="Submit admissions enquiry",
        description="Public endpoint to submit admissions enquiry at /api/v1/enquiries/create/",
        request=EnquiryCreateSerializer,
        responses={201: EnquiryCreateSerializer}
    )
    @action(detail=False, methods=['post'], url_path='create', permission_classes=[permissions.AllowAny])
    def create_enquiry(self, request, *args, **kwargs):
        """Public endpoint to submit admissions enquiry at /api/v1/enquiries/create/"""
        return self.create(request, *args, **kwargs)

    @extend_schema(
        summary="Submit contact enquiry",
        description="Public endpoint to submit contact enquiry at /api/v1/enquiries/contact/",
        request=EnquiryCreateSerializer,
        responses={201: EnquiryCreateSerializer}
    )
    @action(detail=False, methods=['post'], url_path='contact', permission_classes=[permissions.AllowAny])
    def contact_enquiry(self, request, *args, **kwargs):
        """Public endpoint to submit contact enquiry at /api/v1/enquiries/contact/"""
        return self.create(request, *args, **kwargs)

    @extend_schema(
        summary="Submit general enquiry",
        description="Public endpoint to submit enquiry at /api/v1/enquiries/submit/",
        request=EnquiryCreateSerializer,
        responses={201: EnquiryCreateSerializer}
    )
    @action(detail=False, methods=['post'], url_path='submit', permission_classes=[permissions.AllowAny])
    def submit_enquiry(self, request, *args, **kwargs):
        """Public endpoint to submit enquiry at /api/v1/enquiries/submit/"""
        return self.create(request, *args, **kwargs)

    @extend_schema(
        summary="Enquiries statistics",
        description="Returns total and status-breakdown statistics for enquiries",
        responses={200: EnquiryStatsResponseSerializer}
    )
    @action(detail=False, methods=['get'], url_path='stats', permission_classes=[permissions.IsAuthenticated])
    def stats(self, request):
        total = Enquiry.objects.filter(is_deleted=False).count()
        new_count = Enquiry.objects.filter(status='new', is_deleted=False).count()
        contacted_count = Enquiry.objects.filter(status='contacted', is_deleted=False).count()
        resolved_count = Enquiry.objects.filter(status='resolved', is_deleted=False).count()
        return Response({
            'total': total,
            'all': total,
            'new': new_count,
            'contacted': contacted_count,
            'resolved': resolved_count,
            'summary': {
                'all': total,
                'new': new_count,
                'contacted': contacted_count,
                'resolved': resolved_count
            }
        })

    @extend_schema(
        summary="Enquiries counts",
        description="Returns enquiries counts by status",
        responses={200: EnquiryStatsResponseSerializer}
    )
    @action(detail=False, methods=['get'], url_path='counts', permission_classes=[permissions.IsAuthenticated])
    def counts(self, request):
        return self.stats(request)

    @extend_schema(
        summary="Enquiries counts by status",
        description="Returns enquiries counts by status",
        responses={200: EnquiryStatsResponseSerializer}
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def counts_by_status(self, request):
        return self.stats(request)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])


    @extend_schema(
        summary="Update enquiry status",
        description="Update the lead status of an enquiry: 'new', 'contacted', or 'resolved'",
        request=EnquiryStatusUpdateSerializer,
        responses={200: EnquiryStatusChangeResponseSerializer}
    )
    @action(detail=True, methods=['post', 'patch'], url_path='status', permission_classes=[permissions.IsAuthenticated])
    def update_status(self, request, pk=None):
        """
        Update the lead status of an enquiry: 'new', 'contacted', or 'resolved'
        e.g., POST/PATCH /api/v1/enquiries/{id}/status/ {"status": "contacted"}
        """
        enquiry = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = [choice[0] for choice in Enquiry.STATUS_CHOICES]
        
        if not new_status or new_status not in valid_statuses:
            return Response({
                'success': False,
                'error': f"Invalid status '{new_status}'. Allowed values: {valid_statuses}"
            }, status=status.HTTP_400_BAD_REQUEST)

        enquiry.status = new_status
        enquiry.save()
        serializer = EnquiryAdminSerializer(enquiry)
        return Response({
            'success': True,
            'message': f"Lead status updated to '{enquiry.get_status_display()}'.",
            'enquiry': serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Mark enquiry as new",
        description="Helper action: Mark as New Lead",
        request=None,
        responses={200: EnquiryStatusChangeResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='mark-new', permission_classes=[permissions.IsAuthenticated])
    def mark_new(self, request, pk=None):
        """Helper action: Mark as New Lead"""
        enquiry = self.get_object()
        enquiry.status = 'new'
        enquiry.save()
        return Response({
            'success': True,
            'message': "Lead status marked as New Lead.",
            'enquiry': EnquiryAdminSerializer(enquiry).data
        })

    @extend_schema(
        summary="Mark enquiry as contacted",
        description="Helper action: Mark Contacted / In Progress",
        request=None,
        responses={200: EnquiryStatusChangeResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='mark-contacted', permission_classes=[permissions.IsAuthenticated])
    def mark_contacted(self, request, pk=None):
        """Helper action: Mark Contacted / In Progress"""
        enquiry = self.get_object()
        enquiry.status = 'contacted'
        enquiry.save()
        return Response({
            'success': True,
            'message': "Lead status marked as Contacted.",
            'enquiry': EnquiryAdminSerializer(enquiry).data
        })

    @extend_schema(
        summary="Mark enquiry as resolved",
        description="Helper action: Mark Resolved",
        request=None,
        responses={200: EnquiryStatusChangeResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='mark-resolved', permission_classes=[permissions.IsAuthenticated])
    def mark_resolved(self, request, pk=None):
        """Helper action: Mark Resolved"""
        enquiry = self.get_object()
        enquiry.status = 'resolved'
        enquiry.save()
        return Response({
            'success': True,
            'message': "Lead status marked as Resolved.",
            'enquiry': EnquiryAdminSerializer(enquiry).data
        })

    @extend_schema(
        summary="Send email reply",
        description="Send Email Reply action from the Lead Dossier modal",
        request=EnquiryReplySerializer,
        responses={200: EnquiryReplyResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='reply', permission_classes=[permissions.IsAuthenticated])
    def reply(self, request, pk=None):
        """
        Send Email Reply action from the Lead Dossier modal.
        """
        enquiry = self.get_object()
        reply_subject = request.data.get('subject', f"Regarding your Avemaria Enquiry - {enquiry.topic}")
        reply_message = request.data.get('message', '')

        if not reply_message:
            return Response({
                'success': False,
                'error': "Reply message content is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Automatically advance status to 'contacted' if it was 'new'
        if enquiry.status == 'new':
            enquiry.status = 'contacted'
            enquiry.save()

        return Response({
            'success': True,
            'message': f"Reply sent successfully to {enquiry.candidate_name} ({enquiry.email}).",
            'enquiry': EnquiryAdminSerializer(enquiry).data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Export leads CSV",
        description="Alias for /api/v1/enquiries/export/",
        responses={200: bytes}
    )
    @action(detail=False, methods=['get'], url_path='export', permission_classes=[permissions.AllowAny])
    def export_leads(self, request):
        """Alias for /api/v1/enquiries/export/"""
        return self.export_csv(request)

    @extend_schema(
        summary="Export leads CSV (hyphenated)",
        description="Alias for /api/v1/enquiries/export-csv/",
        responses={200: bytes}
    )
    @action(detail=False, methods=['get'], url_path='export-csv', permission_classes=[permissions.AllowAny])
    def export_csv_hyphen(self, request):
        """Alias for /api/v1/enquiries/export-csv/"""
        return self.export_csv(request)

    @extend_schema(
        summary="Export leads CSV",
        description="Export admissions leads as CSV file matching the 'Export Leads (CSV)' admin UI button.",
        responses={200: bytes}
    )
    @action(detail=False, methods=['get'], url_path='export_csv', permission_classes=[permissions.AllowAny])
    def export_csv(self, request):

        """Export admissions leads as CSV file matching the 'Export Leads (CSV)' admin UI button.
        Supports:
        - Authorization: Bearer <token> header
        - ?token=<token> query parameter for direct browser download links
        - ?status=new | contacted | resolved | all
        - ?search=<keyword>
        """
        user = request.user
        token = request.query_params.get('token')

        # Check authentication via header or token query parameter
        if not (user and user.is_authenticated):
            if token:
                try:
                    from rest_framework_simplejwt.tokens import AccessToken
                    from apps.accounts.models import User
                    validated_token = AccessToken(token)
                    user_id = validated_token['user_id']
                    user = User.objects.get(id=user_id, is_active=True)
                except Exception:
                    return Response({'error': 'Invalid or expired download token.'}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                return Response({'error': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Apply filtering (status, search, ordering)
        status_param = request.query_params.get('status')
        if status_param == 'all':
            qs = self.get_queryset()
            search = request.query_params.get('search')
            if search:
                qs = self.filter_queryset(qs)
        else:
            qs = self.filter_queryset(self.get_queryset())

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="admissions_leads.csv"'

        writer = csv.writer(response)
        writer.writerow(['SL NO', 'CANDIDATE NAME', 'EMAIL', 'PHONE', 'TOPIC / COURSE', 'MESSAGE', 'STATUS', 'RECEIVED DATE'])

        for idx, enquiry in enumerate(qs, start=1):
            received_formatted = enquiry.created_at.strftime('%d %b %Y %H:%M')
            writer.writerow([
                idx,
                enquiry.candidate_name,
                enquiry.email,
                enquiry.phone or '',
                enquiry.topic,
                enquiry.message,
                enquiry.get_status_display(),
                received_formatted
            ])

        return response
