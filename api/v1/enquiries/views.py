import csv
from django.http import HttpResponse
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from apps.enquiries.models import Enquiry
from .serializers import EnquiryCreateSerializer, EnquiryAdminSerializer

class EnquiryViewSet(viewsets.ModelViewSet):
    queryset = Enquiry.objects.filter(is_deleted=False)
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['candidate_name', 'email', 'topic', 'message']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at', '-id']

    def get_serializer_class(self):
        if self.action in ['create', 'create_enquiry', 'contact_enquiry', 'submit_enquiry']:
            return EnquiryCreateSerializer
        return EnquiryAdminSerializer

    def get_permissions(self):
        if self.action in ['create', 'create_enquiry', 'contact_enquiry', 'submit_enquiry', 'export_csv', 'export_csv_hyphen']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['post'], url_path='create', permission_classes=[permissions.AllowAny])
    def create_enquiry(self, request, *args, **kwargs):
        """Public endpoint to submit admissions enquiry at /api/v1/enquiries/create/"""
        return self.create(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='contact', permission_classes=[permissions.AllowAny])
    def contact_enquiry(self, request, *args, **kwargs):
        """Public endpoint to submit contact enquiry at /api/v1/enquiries/contact/"""
        return self.create(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='submit', permission_classes=[permissions.AllowAny])
    def submit_enquiry(self, request, *args, **kwargs):
        """Public endpoint to submit enquiry at /api/v1/enquiries/submit/"""
        return self.create(request, *args, **kwargs)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def counts_by_status(self, request):
        total = Enquiry.objects.filter(is_deleted=False).count()
        new_count = Enquiry.objects.filter(status='new', is_deleted=False).count()
        contacted_count = Enquiry.objects.filter(status='contacted', is_deleted=False).count()
        resolved_count = Enquiry.objects.filter(status='resolved', is_deleted=False).count()
        return Response({
            'total': total,
            'new': new_count,
            'contacted': contacted_count,
            'resolved': resolved_count
        })

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

    @action(detail=False, methods=['get'], url_path='export-csv', permission_classes=[permissions.AllowAny])
    def export_csv_hyphen(self, request):
        """Alias for /api/v1/enquiries/export-csv/"""
        return self.export_csv(request)

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
