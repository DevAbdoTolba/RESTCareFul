"""
DoctorProfile = the ISA subtype of accounts.User.

Implemented as a `OneToOneField(..., primary_key=True)` instead of multi-table
inheritance because multi-table inheritance forces a JOIN on every doctor
query — well-known footgun. The 1:1 with the user's PK gives us the same
"one row per doctor" semantics without the overhead.

A DoctorProfile row exists IFF the corresponding user has role='doctor'. The
doctors-app registration endpoint creates the row atomically with the user.
"""
from django.conf import settings
from django.db import models


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='doctor_profile',
    )
    specialty = models.ForeignKey(
        'specialties.Specialty',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='doctors',
    )
    # TextField (not URLField) on purpose: the React app may send either a real
    # link OR a base64 `data:` URL for an uploaded file, and URLField's
    # validator rejects the latter. Boundary-validated in the serializer.
    resume_url = models.TextField(blank=True)
    license_url = models.TextField(blank=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'Doctor<{self.user.email}>'


class DoctorAvailability(models.Model):
    """An open window the doctor declares — patients can book inside it."""
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='availabilities')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'doctor availabilities'
        ordering = ['date', 'start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'date', 'start_time'],
                name='uniq_doctor_slot',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.doctor.user.email} {self.date} {self.start_time}-{self.end_time}'
