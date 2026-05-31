"""
URL routes for the ratings slice. Mounted at /api/v1/ratings/.

Owner: see .github/CODEOWNERS. Add endpoints here only.
"""

from django.urls import path

from .views import CreateRatingView, DoctorRatingsView

app_name = 'ratings'

urlpatterns = [
    path('', CreateRatingView.as_view(), name='create'),
    path('doctor/<int:pk>/', DoctorRatingsView.as_view(), name='doctor'),
]
