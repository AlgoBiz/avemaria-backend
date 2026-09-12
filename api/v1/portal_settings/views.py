from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.portal_settings.models import PortalSetting
from .serializers import PortalSettingSerializer

class PortalSettingView(APIView):
    serializer_class = PortalSettingSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        tags=['Portal Settings'],
        summary="Retrieve Portal Configuration & Settings",
        description="Returns global portal branding, contact details, social links, SEO tags, and feature flags.",
        responses={200: PortalSettingSerializer}
    )
    def get(self, request):
        setting = PortalSetting.load()
        serializer = PortalSettingSerializer(setting)
        return Response(serializer.data)

    @extend_schema(
        tags=['Portal Settings'],
        summary="Update Portal Configuration & Settings (PUT)",
        description="Updates global portal settings, email contacts, phone numbers, addresses, and platform flags.",
        request=PortalSettingSerializer,
        responses={200: PortalSettingSerializer, 400: PortalSettingSerializer}
    )
    def put(self, request):
        setting = PortalSetting.load()
        serializer = PortalSettingSerializer(instance=setting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Portal Settings'],
        summary="Partially Update Portal Configuration & Settings (PATCH)",
        description="Partially updates individual portal configuration parameters.",
        request=PortalSettingSerializer,
        responses={200: PortalSettingSerializer, 400: PortalSettingSerializer}
    )
    def patch(self, request):
        return self.put(request)
