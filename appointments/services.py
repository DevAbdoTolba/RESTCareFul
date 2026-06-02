"""Appointment lifecycle helpers that run outside a single request body."""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Appointment


@transaction.atomic
def expire_overdue_appointments():
    """Auto-expire bookings the doctor never confirmed in time.

    A PENDING appointment whose date+time has passed means the doctor never
    accepted it. We flip it to OUTDATED and revoke any money: the patient
    shouldn't pay for a visit that never got confirmed, and a refunded payment
    drops out of the admin dashboard totals (which only sum PAID payments).

    Idempotent and cheap (early return when nothing is overdue), so it's safe to
    call on the appointment list + dashboard reads instead of needing a cron.
    Returns the number of appointments expired.
    """
    from payments.models import Payment  # local import: payments depends on appointments

    now = timezone.now()
    overdue = Appointment.objects.filter(status=Appointment.Status.PENDING).filter(
        Q(date__lt=now.date()) | Q(date=now.date(), time__lte=now.time())
    )
    ids = list(overdue.values_list('id', flat=True))
    if not ids:
        return 0

    # Revoke the money first (refund anything that was paid) ...
    Payment.objects.filter(appointment_id__in=ids, status=Payment.Status.PAID).update(
        status=Payment.Status.REFUNDED
    )
    # ... then mark the appointments outdated + unpaid.
    Appointment.objects.filter(id__in=ids).update(
        status=Appointment.Status.OUTDATED, paid=False, amount_paid=0
    )
    return len(ids)


def revoke_payment(appt):
    """Refund a single appointment's money and clear its paid flag.

    Any PAID payment becomes REFUNDED (so it drops out of the dashboard totals)
    and the appointment reads as unpaid again. Used when a booking is cancelled.
    Returns True if there was money to give back.
    """
    from payments.models import Payment  # local import: payments depends on appointments

    refunded = Payment.objects.filter(appointment=appt, status=Payment.Status.PAID).update(
        status=Payment.Status.REFUNDED
    )
    if appt.paid or refunded:
        appt.paid = False
        appt.amount_paid = 0
        appt.save(update_fields=['paid', 'amount_paid', 'updated_at'])
    return bool(refunded)
