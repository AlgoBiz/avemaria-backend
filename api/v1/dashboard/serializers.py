from rest_framework import serializers
from api.v1.enquiries.serializers import EnquiryAdminSerializer
from api.v1.courses.serializers import CourseListSerializer


class DashboardStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_courses = serializers.IntegerField()
    active_users = serializers.IntegerField()
    total_documents_uploaded = serializers.IntegerField()
    categories_count = serializers.IntegerField()
    resource_pools_count = serializers.IntegerField(required=False, default=0)
    new_enquiries_count = serializers.IntegerField(required=False, default=0)
    total_enquiries = serializers.IntegerField(required=False, default=0)
    packs_label = serializers.CharField(required=False)
    courses_label = serializers.CharField(required=False)
    recent_enquiries = EnquiryAdminSerializer(many=True)
    programmes_catalog = CourseListSerializer(many=True)
    kpis = serializers.DictField(required=False)
    chart_data = serializers.ListField(child=serializers.DictField(), required=False)
    item_wise_performance = serializers.ListField(child=serializers.DictField(), required=False)


DashboardOverviewResponseSerializer = DashboardStatsSerializer
