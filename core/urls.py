"""URL routes for the core slice. Mounted at /api/v1/settings/ from config.urls."""

from django.urls import path

from .views import SiteSettingsView

app_name = 'core'

urlpatterns = [
    path('', SiteSettingsView.as_view(), name='site-settings'),
]
