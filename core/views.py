from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdmin

from .models import SiteSettings


class SiteSettingsView(APIView):
    """GET (public) the active theme + PUT (admin) to change it site-wide.

    Public read so every visitor — signed-in or not — renders in the theme the
    admin chose. Only an admin may change it, and the change sticks for everyone.
    """

    def get_permissions(self):
        return [IsAdmin()] if self.request.method in ('PUT', 'PATCH') else [AllowAny()]

    def get(self, request):
        return Response({'theme': SiteSettings.load().theme})

    def put(self, request):
        theme = request.data.get('theme')
        if not theme or not isinstance(theme, str):
            return Response({'detail': 'theme is required.'}, status=status.HTTP_400_BAD_REQUEST)
        settings_row = SiteSettings.load()
        settings_row.theme = theme
        settings_row.save(update_fields=['theme', 'updated_at'])
        return Response({'theme': settings_row.theme})
