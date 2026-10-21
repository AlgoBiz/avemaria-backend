from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WebinarViewSet

router = DefaultRouter()
router.register(r'', WebinarViewSet, basename='webinars')

urlpatterns = [
    path('', include(router.urls)),
]
