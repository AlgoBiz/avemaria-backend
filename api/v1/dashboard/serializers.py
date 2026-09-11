from rest_framework import serializers
from apps.enquiries.models import Enquiry
from apps.courses.models import Course
from api.v1.enquiries.serializers import EnquiryAdminSerializer
from api.v1.courses.serializers import CourseListSerializer

class DashboardStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_courses = serializers.IntegerField()
    active_users = serializers.IntegerField()
    total_documents_uploaded = serializers.IntegerField()
    categories_count = serializers.IntegerField()
    recent_enquiries = EnquiryAdminSerializer(many=True)
    programmes_catalog = CourseListSerializer(many=True)
