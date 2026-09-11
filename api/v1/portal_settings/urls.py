from django.urls import path
from .views import PortalSettingView

urlpatterns = [
    path('', PortalSettingView.as_view(), name='portal_settings'),
]
