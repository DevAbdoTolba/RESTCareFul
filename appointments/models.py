from django.conf import settings
from django.db import models


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'  # patient requested, doctor not yet confirmed
        CONFIRMED = 'confirmed', 'Confirmed'  # doctor accepted
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'  # visit happened

    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)  # the doctor's notes for the patient

    # PayPal sandbox payment snapshot on the appointment itself, so a booking
    # carries its own "was this paid?" answer without joining `payments`.
    paid = models.BooleanField(default=False)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='appointments_as_patient',
    )
    doctor = models.ForeignKey(
        'doctors.DoctorProfile',
        on_delete=models.PROTECT,
        related_name='appointments',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time']
        constraints = [
            # One doctor, one slot — db-level guard against double-booking races.
            models.UniqueConstraint(
                fields=['doctor', 'date', 'time'],
                name='uniq_doctor_slot_booked',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.patient.email} @ {self.doctor} on {self.date} {self.time}'
