"""
URL routes for the doctors slice. Mounted at /api/v1/doctors/ from config.urls.

Owner: see .github/CODEOWNERS. Add endpoints here only — do NOT touch
config/urls.py for routing changes inside this slice. That's how we keep PRs
inside this app from ever conflicting with another teammate's PR.
"""

from django.urls import path  # noqa: F401  (kept handy for the first endpoint)

app_name = 'doctors'

urlpatterns = []
