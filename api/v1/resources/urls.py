from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter
from .views import PaidResourceViewSet

router = DefaultRouter()
router.register(r'', PaidResourceViewSet, basename='resource')

urlpatterns = [
    path('categories/create/', PaidResourceViewSet.as_view({'post': 'create_resource_category'}), name='resource-category-create'),
    path('categories/minimal/', PaidResourceViewSet.as_view({'get': 'resource_categories_minimal'}), name='resource-categories-minimal'),
    re_path(r'^categories/(?P<cat_lookup>(?!create$|minimal$)[^/.]+)/?$', PaidResourceViewSet.as_view({
        'get': 'category_detail',
        'patch': 'category_detail',
        'put': 'category_detail',
        'delete': 'category_detail'
    }), name='resource-category-detail-any'),
    path('', include(router.urls)),
]
