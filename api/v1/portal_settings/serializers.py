from rest_framework import serializers
from apps.portal_settings.models import PortalSetting

class PortalSettingSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uuid_str', read_only=True)

    class Meta:
        model = PortalSetting
        fields = (
            'id', 'institution_legal_name', 'admissions_email',
            'direct_telephone', 'whatsapp_desk', 'working_hours',
            'campus_address', 'is_active', 'is_deleted', 'created_at', 'updated_at'
        )
