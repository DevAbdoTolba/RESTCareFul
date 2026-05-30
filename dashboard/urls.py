"""
URL routes for the admin dashboard slice. Mounted at /api/v1/dashboard/.

Owner: see .github/CODEOWNERS. Add endpoints here only.
"""

from django.urls import path

from .views import DashboardMetricsView

app_name = 'dashboard'

urlpatterns = [
    path('metrics/', DashboardMetricsView.as_view(), name='metrics'),
]
