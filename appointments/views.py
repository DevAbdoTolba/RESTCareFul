from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsPatient
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
        slot = ser.validated_data['availability']

        try:
            with transaction.atomic():
                locked = (
                    DoctorAvailability.objects.select_for_update().get(pk=slot.pk)
                )
                if not locked.is_available:
                    return Response(
                        {'detail': 'That slot was just taken.'},
                        status=status.HTTP_409_CONFLICT,
                    )
                appointment = Appointment.objects.create(
                    patient=request.user,
                    doctor=locked.doctor,
                    date=locked.date,
                    time=locked.start_time,
                    notes=ser.validated_data['notes'],
                )
                locked.is_available = False
                locked.save(update_fields=['is_available'])
        except IntegrityError:
            return Response(
                {'detail': 'This doctor is already booked at that time.'},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED
        )
