from rest_framework import serializers
from apps.students.models import Student

class StudentSerializer(serializers.ModelSerializer):
    institution_and_year = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    registered_date_formatted = serializers.SerializerMethodField()

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

