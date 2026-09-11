from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GalleryItemViewSet

router = DefaultRouter()
router.register(r'', GalleryItemViewSet, basename='gallery')

urlpatterns = [
    path('', include(router.urls)),
]
