from django.urls import path, include

urlpatterns = [
    path('auth/', include('api.v1.auth.urls')),
    path('dashboard/', include('api.v1.dashboard.urls')),
    path('categories/', include('api.v1.categories.urls')),
    path('courses/', include('api.v1.courses.urls')),
    path('resources/', include('api.v1.resources.urls')),
    path('testimonials/', include('api.v1.testimonials.urls')),
    path('gallery/', include('api.v1.gallery.urls')),
    path('enquiries/', include('api.v1.enquiries.urls')),
    path('blogs/', include('api.v1.blogs.urls')),
    path('students/', include('api.v1.students.urls')),
    path('settings/', include('api.v1.portal_settings.urls')),
]
