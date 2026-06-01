"""
URL routes for the doctors slice. Mounted at /api/v1/doctors/ from config.urls.

Owner: see .github/CODEOWNERS. Add endpoints here only — do NOT touch
config/urls.py for routing changes inside this slice. That's how we keep PRs
inside this app from ever conflicting with another teammate's PR.
"""

from django.urls import path

from .views import (
    AdminUpdateRequestListView,
    ApprovedDoctorDetailView,
    ApprovedDoctorListView,
    ApproveUpdateRequestView,
    BestDoctorsView,
    DoctorOpenSlotsView,
    MyAvailabilityDeleteView,
    MyAvailabilityView,
    MyDoctorProfileView,
    MyUpdateRequestView,
    RejectUpdateRequestView,
)

app_name = 'doctors'

urlpatterns = [
    path('', ApprovedDoctorListView.as_view(), name='list'),
    path('best/', BestDoctorsView.as_view(), name='best'),
    # 'me/...' before '<int:pk>/' so the literal isn't swallowed as an id.
    path('me/', MyDoctorProfileView.as_view(), name='me'),
    path('me/availability/', MyAvailabilityView.as_view(), name='my-availability'),
    path(
        'me/availability/<int:pk>/',
        MyAvailabilityDeleteView.as_view(),
        name='my-availability-delete',
    ),
    path('me/update-requests/', MyUpdateRequestView.as_view(), name='my-update-requests'),
    path('update-requests/', AdminUpdateRequestListView.as_view(), name='admin-update-requests'),
    path(
        'update-requests/<int:pk>/approve/',
        ApproveUpdateRequestView.as_view(),
        name='update-request-approve',
    ),
    path(
        'update-requests/<int:pk>/reject/',
        RejectUpdateRequestView.as_view(),
        name='update-request-reject',
    ),
    path('<int:pk>/', ApprovedDoctorDetailView.as_view(), name='detail'),
    path('<int:pk>/availability/', DoctorOpenSlotsView.as_view(), name='open-slots'),
]
