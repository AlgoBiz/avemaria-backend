from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaidResourceViewSet

router = DefaultRouter()
router.register(r'', PaidResourceViewSet, basename='resource')

urlpatterns = [
    path('categories/create/', PaidResourceViewSet.as_view({'post': 'create_resource_category'}), name='resource-category-create'),
    path('categories/minimal/', PaidResourceViewSet.as_view({'get': 'resource_categories_minimal'}), name='resource-categories-minimal'),
    path('', include(router.urls)),
]
