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
    path('api/v1/auth/', include('accounts.urls', namespace='accounts')),
    # Domain apps mount here as their owners ship their first PR.
]
