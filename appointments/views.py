from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.pagination import StandardResultsSetPagination
from core.permissions import IsDoctor, IsPatient
from doctors.models import DoctorAvailability

from .models import Appointment
from .serializers import AppointmentSerializer, BookAppointmentSerializer


class BookAppointmentView(APIView):
    """POST /api/v1/appointments/book/ - a patient books an open slot.

    The slot is locked + flipped to unavailable inside a transaction, and the
    DB UniqueConstraint(doctor, date, time) is the final guard against two
    patients racing for the same slot.
    """

    permission_classes = [IsPatient]

    def post(self, request):
        ser = BookAppointmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        prof = data['doctor_profile']

        with transaction.atomic():
            existing = (
                Appointment.objects.select_for_update()
                .filter(doctor=prof, date=data['date'], time=data['time'])
                .first()
            )
            if existing is not None:
                if existing.status != Appointment.Status.CANCELLED:
                    return Response(
                        {'detail': 'That slot is already booked.'},
                        status=status.HTTP_409_CONFLICT,
                    )
                # Re-open a previously-cancelled slot for the new patient.
                existing.patient = request.user
                existing.status = Appointment.Status.PENDING
                existing.notes = data['notes']
                existing.paid = False
                existing.amount_paid = 0
                existing.save()
                appointment = existing
            else:
                appointment = Appointment.objects.create(
                    patient=request.user,
                    doctor=prof,
                    date=data['date'],
                    time=data['time'],
                    notes=data['notes'],
                )

        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)


class MyAppointmentsView(generics.ListAPIView):
    """GET /api/v1/appointments/ - the caller's appointments (patient or doctor).

    Same component on the frontend for both roles, so one endpoint serves both.
    Filters: ?status= , ?month=YYYY-MM , ?search= (doctor/patient name, specialty,
    notes). Paginated 10 per page with ?page_size= for the "load more" button.
    """

    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related('doctor__user', 'doctor__specialty', 'patient')
        if user.role == User.Role.DOCTOR:
            qs = qs.filter(doctor_id=user.pk)
        elif user.role == User.Role.PATIENT:
            qs = qs.filter(patient=user)
        # admins see every appointment (drives the admin appointments page)

        params = self.request.query_params
        if params.get('status'):
            qs = qs.filter(status=params['status'])

        month = params.get('month')  # expects YYYY-MM
        if month and '-' in month:
            year, mon = month.split('-')[:2]
            qs = qs.filter(date__year=year, date__month=mon)

        search = params.get('search')
        if search:
            qs = qs.filter(
                Q(doctor__user__first_name__icontains=search)
                | Q(doctor__user__last_name__icontains=search)
                | Q(patient__first_name__icontains=search)
                | Q(patient__last_name__icontains=search)
                | Q(doctor__specialty__name__icontains=search)
                | Q(notes__icontains=search)
            )
        return qs


class CancelAppointmentView(APIView):
    """POST /api/v1/appointments/<id>/cancel/ - patient cancels a pending booking.

    Only allowed while still 'pending' (the requested phase). Cancelling frees
    the doctor's availability window back up for someone else.
    """

    permission_classes = [IsPatient]

    def post(self, request, pk):
        appt = get_object_or_404(Appointment, pk=pk, patient=request.user)
        if appt.status != Appointment.Status.PENDING:
            return Response(
                {'detail': 'Only a pending appointment can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appt.status = Appointment.Status.CANCELLED
        appt.save(update_fields=['status', 'updated_at'])
        DoctorAvailability.objects.filter(
            doctor=appt.doctor, date=appt.date, start_time=appt.time
        ).update(is_available=True)
        return Response(AppointmentSerializer(appt).data)


class ManageAppointmentView(APIView):
    """POST /api/v1/appointments/<id>/manage/ - the doctor moves it along.

    Body: {"status": "confirmed|completed|cancelled", "notes": "..."}.
    """

    permission_classes = [IsDoctor]

    ALLOWED = {
        Appointment.Status.CONFIRMED,
        Appointment.Status.COMPLETED,
        Appointment.Status.CANCELLED,
    }

    def post(self, request, pk):
        appt = get_object_or_404(Appointment, pk=pk, doctor_id=request.user.pk)
        new_status = request.data.get('status')
        if new_status not in self.ALLOWED:
            return Response(
                {'detail': f'status must be one of {sorted(self.ALLOWED)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appt.status = new_status
        if 'notes' in request.data:
            appt.notes = request.data['notes']
        appt.save(update_fields=['status', 'notes', 'updated_at'])
        return Response(AppointmentSerializer(appt).data)
