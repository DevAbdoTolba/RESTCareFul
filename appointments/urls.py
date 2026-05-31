"""
URL routes for the appointments slice. Mounted at /api/v1/appointments/.

Owner: see .github/CODEOWNERS. Add endpoints here only.
"""

from django.urls import path

from .views import BookAppointmentView, MyAppointmentsView

app_name = 'appointments'

urlpatterns = [
    path('', MyAppointmentsView.as_view(), name='mine'),
    path('book/', BookAppointmentView.as_view(), name='book'),
]
