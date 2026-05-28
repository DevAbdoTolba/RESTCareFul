"""
Root URL config.

Convention: every API URL lives under `/api/v1/<app>/`. Per-app urls are
mounted from here and owned by the matching CODEOWNER — keeps route conflicts
between teammates impossible unless someone changes this file.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth + user-me endpoints (accounts slice).
    path('api/v1/auth/', include('accounts.urls', namespace='accounts')),
    # Domain slices are pre-mounted with empty urlpatterns so each owner only
    # edits their own <app>/urls.py — never this file. Routing changes inside a
    # slice never conflict with another slice's PR.
    path('api/v1/doctors/', include('doctors.urls', namespace='doctors')),
    path('api/v1/specialties/', include('specialties.urls', namespace='specialties')),
    path('api/v1/appointments/', include('appointments.urls', namespace='appointments')),
    path('api/v1/payments/', include('payments.urls', namespace='payments')),
    path('api/v1/ratings/', include('ratings.urls', namespace='ratings')),
    path('api/v1/dashboard/', include('dashboard.urls', namespace='dashboard')),
]
