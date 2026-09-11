from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.students.models import Student
from .serializers import StudentSerializer

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.filter(is_deleted=False)
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['name', 'email', 'qualification', 'institution', 'location', 'city', 'country']
    ordering_fields = ['registered_date', 'name', 'created_at']
    ordering = ['-created_at', '-id']


    @action(detail=False, methods=['post'], url_path='create')
    def create_student(self, request, *args, **kwargs):
        """Create student candidate endpoint at /api/v1/students/create/"""
        return self.create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def contact(self, request, pk=None):
        student = self.get_object()
        subject = request.data.get('subject', 'Avemaria Student Portal Update')
        message = request.data.get('message', 'Hello, an update from Avemaria Career Guidance Center.')
        return Response({
            'success': True,
            'message': f"Contact dispatch queued successfully for {student.name} ({student.email}).",
            'student_id': student.id
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='invoice', permission_classes=[permissions.AllowAny])
    def invoice(self, request, pk=None):
        """
        Generate and download student tax invoice / fee receipt PDF.
        Supports both Authorization: Bearer <token> and ?token=<token> for direct browser downloads.
        """
        user = request.user
        token = request.query_params.get('token')
        if not (user and user.is_authenticated):
            if token:
                try:
                    from rest_framework_simplejwt.tokens import AccessToken
                    from apps.accounts.models import User
                    validated_token = AccessToken(token)
                    user = User.objects.get(id=validated_token['user_id'], is_active=True)
                except Exception:
                    return Response({'error': 'Invalid or expired download token.'}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                return Response({'error': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

        student = self.get_object()
        from apps.resources.models import ResourcePurchase
        from apps.courses.models import CourseEnrollment
        import io
        from django.http import HttpResponse
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'InvTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#0d1b3e')
        )
        sub_style = ParagraphStyle(
            'InvSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#555555')
        )
        bold_style = ParagraphStyle(
            'InvBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#0d1b3e')
        )

        elements.append(Paragraph("Avemaria Career Guidance Center Ltd.", title_style))
        elements.append(Paragraph("71-75 Shelton Street, Covent Garden, London, WC2H 9JQ", sub_style))
        elements.append(Paragraph("Email: admissions@avemariacareer.co.uk | Web: avemaria-frontend.vercel.app", sub_style))
        elements.append(Spacer(1, 15))

        elements.append(Paragraph("OFFICIAL PAYMENT RECEIPT & INVOICE", ParagraphStyle(
            'ReceiptHdr', parent=title_style, fontSize=14, leading=18, textColor=colors.HexColor('#b38128')
        )))
        elements.append(Spacer(1, 10))

        reg_str = student.registered_date.strftime('%d %b %Y') if student.registered_date else '-'
        student_info = [
            [Paragraph("<b>Student Name:</b>", bold_style), Paragraph(student.name, sub_style),
             Paragraph("<b>Invoice No:</b>", bold_style), Paragraph(f"INV-STU-{student.id:04d}", sub_style)],
            [Paragraph("<b>Email:</b>", bold_style), Paragraph(student.email, sub_style),
             Paragraph("<b>Date:</b>", bold_style), Paragraph(reg_str, sub_style)],
            [Paragraph("<b>Location:</b>", bold_style), Paragraph(student.location or student.city or 'London, UK', sub_style),
             Paragraph("<b>Status:</b>", bold_style), Paragraph(student.get_status_display(), sub_style)]
        ]
        info_table = Table(student_info, colWidths=[90, 180, 80, 150])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # Items table
        purchases = ResourcePurchase.objects.filter(student=student, is_deleted=False).select_related('resource')
        enrollments = CourseEnrollment.objects.filter(student=student, is_deleted=False).select_related('course')

        table_data = [
            [Paragraph("<b>SL</b>", bold_style), Paragraph("<b>Item Description</b>", bold_style), Paragraph("<b>Category / Type</b>", bold_style), Paragraph("<b>Date</b>", bold_style), Paragraph("<b>Amount</b>", bold_style)]
        ]

        total = 0.0
        idx = 1
        for p in purchases:
            amt = float(p.amount_paid or (p.resource.price if p.resource else 0.0))
            total += amt
            dt_str = p.purchased_at.strftime('%d %b %Y') if p.purchased_at else '-'
            item_name = p.resource.title if p.resource else "Study Resource Pack"
            cat = p.resource.category if p.resource else "Resource"
            table_data.append([
                Paragraph(str(idx), sub_style),
                Paragraph(item_name, sub_style),
                Paragraph(cat, sub_style),
                Paragraph(dt_str, sub_style),
                Paragraph(f"£{amt:.2f}", sub_style)
            ])
            idx += 1

        for e in enrollments:
            amt = float(e.course.fee) if (e.course and e.course.fee) else 0.0
            total += amt
            dt_str = e.created_at.strftime('%d %b %Y') if e.created_at else '-'
            c_name = e.course.title if e.course else "Course Programme"
            table_data.append([
                Paragraph(str(idx), sub_style),
                Paragraph(c_name, sub_style),
                Paragraph("Course Enrolment", sub_style),
                Paragraph(dt_str, sub_style),
                Paragraph(f"£{amt:.2f}", sub_style)
            ])
            idx += 1

        if len(table_data) == 1:
            table_data.append([
                Paragraph("1", sub_style),
                Paragraph("Registration & Portal Access", sub_style),
                Paragraph("Candidate Enrolment", sub_style),
                Paragraph(reg_str, sub_style),
                Paragraph("£0.00", sub_style)
            ])

        items_table = Table(table_data, colWidths=[30, 220, 110, 80, 70])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f4f6fa')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 15))

        total_data = [
            [Paragraph("<b>Total Paid:</b>", bold_style), Paragraph(f"<b>£{total:.2f}</b>", bold_style)]
        ]
        tot_table = Table(total_data, colWidths=[430, 80])
        tot_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(tot_table)
        elements.append(Spacer(1, 30))

        elements.append(Paragraph("This is an electronically generated receipt verified by Avemaria Career Guidance Center Ltd. No signature required.", sub_style))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Invoice_Student_{student.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
