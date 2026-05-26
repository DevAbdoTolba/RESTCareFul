from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Rating(models.Model):
    """
    One rating per completed appointment — the appointment IS the natural PK,
    enforced via `OneToOneField(primary_key=True)`.
    """

    appointment = models.OneToOneField(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='rating',
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ratings_given',
    )
    doctor = models.ForeignKey(
        'doctors.DoctorProfile',
        on_delete=models.PROTECT,
        related_name='ratings_received',
    )
    stars = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.stars}★ for {self.doctor}'
