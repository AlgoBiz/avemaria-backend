from django.urls import path
from .views import DashboardOverviewView

urlpatterns = [
    path('', DashboardOverviewView.as_view(), name='dashboard_overview_root'),
    path('overview/', DashboardOverviewView.as_view(), name='dashboard_overview'),
]
