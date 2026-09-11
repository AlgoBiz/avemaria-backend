from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.portal_settings.models import PortalSetting
from .serializers import PortalSettingSerializer

class PortalSettingView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get(self, request):
        setting = PortalSetting.load()
        serializer = PortalSettingSerializer(setting)
        return Response(serializer.data)

    def put(self, request):
        setting = PortalSetting.load()
        serializer = PortalSettingSerializer(instance=setting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)

