from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter
from .views import BlogViewSet, BlogCategoryViewSet

router = DefaultRouter()
router.register(r'categories', BlogCategoryViewSet, basename='blog-categories')
router.register(r'', BlogViewSet, basename='blog')

urlpatterns = [
    re_path(r'^categories/(?P<pk>[^/.]+)/?$', BlogCategoryViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='blog-category-detail-any'),
    path('', include(router.urls)),
]

