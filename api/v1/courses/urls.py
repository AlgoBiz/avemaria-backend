from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourseViewSet

router = DefaultRouter()
router.register(r'', CourseViewSet, basename='course')

urlpatterns = [
    path('categories/', include('api.v1.categories.urls')),
    path('', include(router.urls)),
]
