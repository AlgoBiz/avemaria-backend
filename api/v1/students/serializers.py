from rest_framework import serializers
from apps.students.models import Student
from apps.resources.models import ResourcePurchase
from apps.courses.models import CourseEnrollment

class StudentSerializer(serializers.ModelSerializer):
    institution_and_year = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    registered_date_formatted = serializers.SerializerMethodField()
    purchase_date = serializers.SerializerMethodField()
    purchase_date_formatted = serializers.SerializerMethodField()
    invoice_download_url = serializers.SerializerMethodField()
    has_invoice = serializers.SerializerMethodField()
    total_purchases_count = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = '__all__'
        read_only_fields = ('id', 'registered_date', 'created_at', 'updated_at')

    def get_registered_date_formatted(self, obj):
        if obj.registered_date:
            day = obj.registered_date.strftime('%d').lstrip('0')
            month_year = obj.registered_date.strftime('%b %Y')
            return f"{day} {month_year}"
        return ""

    def _get_latest_purchase(self, obj):
        if not hasattr(obj, '_cached_latest_purchase'):
            purchase = (
                ResourcePurchase.objects.filter(student=obj, is_deleted=False)
                .order_by('-purchased_at')
                .first()
            )
            obj._cached_latest_purchase = purchase
        return obj._cached_latest_purchase

    def get_purchase_date(self, obj):
        latest = self._get_latest_purchase(obj)
        if latest and latest.purchased_at:
            return latest.purchased_at.isoformat()
        enrollment = CourseEnrollment.objects.filter(student=obj, is_deleted=False).order_by('-created_at').first()
        if enrollment and enrollment.created_at:
            return enrollment.created_at.isoformat()
        return None

    def get_purchase_date_formatted(self, obj):
        latest = self._get_latest_purchase(obj)
        dt = None
        if latest and latest.purchased_at:
            dt = latest.purchased_at
        else:
            enrollment = CourseEnrollment.objects.filter(student=obj, is_deleted=False).order_by('-created_at').first()
            if enrollment and enrollment.created_at:
                dt = enrollment.created_at

        if dt:
            day = dt.strftime('%d').lstrip('0')
            month = dt.strftime('%b')
            if month == 'Sep':
                month = 'Sept'
            return f"{day} {month} {dt.strftime('%Y')}"
        return None

    def get_invoice_download_url(self, obj):
        request = self.context.get('request')
        url = f"/api/v1/students/{obj.id}/invoice/"
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_has_invoice(self, obj):
        return bool(self._get_latest_purchase(obj) or CourseEnrollment.objects.filter(student=obj, is_deleted=False).exists())

    def get_total_purchases_count(self, obj):
        p_count = ResourcePurchase.objects.filter(student=obj, is_deleted=False).count()
        e_count = CourseEnrollment.objects.filter(student=obj, is_deleted=False).count()
        return p_count + e_count

