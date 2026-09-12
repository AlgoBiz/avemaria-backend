from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GalleryItemViewSet, GalleryCategoryViewSet

router = DefaultRouter()
router.register(r'categories', GalleryCategoryViewSet, basename='gallery-categories')
router.register(r'', GalleryItemViewSet, basename='gallery')

urlpatterns = [
    path('', include(router.urls)),
]

