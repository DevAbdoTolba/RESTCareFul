from django.conf import settings
from django.db import models


class Payment(models.Model):
    """
    The PayPal ledger row that backs an appointment booking.

    Two PayPal ids are stored separately because they arrive at different
    points in the flow: `paypal_order_id` is returned by `create order`,
    `paypal_capture_id` only after `capture`. Both are useful for refunds and
    reconciliation. The admin dashboard sums `amount` where status='paid' to
    compute total revenue (12% cut at the app layer).
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        REFUNDED = 'refunded', 'Refunded'
        FAILED = 'failed', 'Failed'

    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        related_name='payments',
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payments',
    )
    doctor = models.ForeignKey(
        'doctors.DoctorProfile',
        on_delete=models.PROTECT,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    paypal_order_id = models.CharField(max_length=64, blank=True)
    paypal_capture_id = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Payment<{self.amount} {self.status}>'
