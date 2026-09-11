from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaidResourceViewSet

router = DefaultRouter()
router.register(r'', PaidResourceViewSet, basename='resource')

urlpatterns = [
    path('', include(router.urls)),
]
