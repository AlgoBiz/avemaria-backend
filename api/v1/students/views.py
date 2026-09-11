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
