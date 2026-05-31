"""
URL routes for the appointments slice. Mounted at /api/v1/appointments/.

Owner: see .github/CODEOWNERS. Add endpoints here only.
"""

from django.urls import path

from .views import (
    BookAppointmentView,
    CancelAppointmentView,
    ManageAppointmentView,
    MyAppointmentsView,
)

app_name = 'appointments'

urlpatterns = [
    path('', MyAppointmentsView.as_view(), name='mine'),
    path('book/', BookAppointmentView.as_view(), name='book'),
    path('<int:pk>/cancel/', CancelAppointmentView.as_view(), name='cancel'),
    path('<int:pk>/manage/', ManageAppointmentView.as_view(), name='manage'),
]
