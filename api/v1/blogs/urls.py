from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter
from .views import BlogViewSet, BlogCategoryViewSet

router = DefaultRouter()
router.register(r'categories', BlogCategoryViewSet, basename='blog-categories')
router.register(r'', BlogViewSet, basename='blog')

urlpatterns = [
    re_path(r'^categories/create/?$', BlogCategoryViewSet.as_view({'post': 'create_category'}), name='blog-category-create'),
    re_path(r'^categories/minimal/?$', BlogCategoryViewSet.as_view({'get': 'minimal'}), name='blog-category-minimal'),
    re_path(r'^categories/(?P<pk>(?!create$|minimal$)[^/.]+)/?$', BlogCategoryViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='blog-category-detail-any'),
    path('', include(router.urls)),
]

