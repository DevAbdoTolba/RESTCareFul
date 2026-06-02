"""Email notifications — best-effort, never break the request that triggers them.

Each function takes plain values (no model imports) so this module stays free of
cross-slice dependencies. Sending is wrapped so an SMTP hiccup (or no creds at
all -> console backend) can't bubble up into the API response.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

SIGNATURE = '\n\n— The useCare team'


def _send(to_email, subject, body):
    if not to_email:
        return
    try:
        send_mail(
            subject,
            body + SIGNATURE,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=False,
        )
    except Exception:
        # Notifications are best-effort — a send failure must never break the flow.
        logger.exception('Failed to send notification email to %s', to_email)


def notify_account_created(email, name):
    _send(
        email,
        'Welcome to useCare 🎉',
        f'Hi {name},\n\nYour useCare account has been created successfully. '
        'You can now sign in and start using the platform.',
    )


def notify_account_banned(email, name):
    _send(
        email,
        'Your useCare account has been suspended',
        f'Hi {name},\n\nYour useCare account has been suspended by an administrator, so you '
        "won't be able to sign in for now. If you think this was a mistake, please reply to "
        'this email and our team will look into it.',
    )


def notify_account_unbanned(email, name):
    _send(
        email,
        'Your useCare account has been reinstated',
        f'Hi {name},\n\nGood news — your useCare account has been reinstated and you can sign '
        'in again. Welcome back!',
    )


def notify_doctor_new_appointment(doctor_email, doctor_name, patient_name, date, time):
    _send(
        doctor_email,
        'New appointment request',
        f'Hi Dr. {doctor_name},\n\n{patient_name} has booked an appointment with you on '
        f'{date} at {time}. Sign in to confirm it once the payment is in.',
    )


def notify_patient_appointment_confirmed(patient_email, patient_name, doctor_name, date, time):
    _send(
        patient_email,
        'Your appointment is confirmed',
        f'Hi {patient_name},\n\nDr. {doctor_name} has confirmed your appointment on '
        f'{date} at {time}. We look forward to seeing you.',
    )


def notify_specialty_decision(doctor_email, doctor_name, specialty_name, approved):
    if approved:
        subject = 'Your proposed specialty was approved'
        body = (
            f'Hi Dr. {doctor_name},\n\nThe specialty you proposed, "{specialty_name}", has been '
            'approved and is now available on useCare.'
        )
    else:
        subject = 'Update on your proposed specialty'
        body = (
            f'Hi Dr. {doctor_name},\n\nAfter review, the specialty you proposed, '
            f'"{specialty_name}", was not approved this time.'
        )
    _send(doctor_email, subject, body)


def notify_doc_update_decision(doctor_email, doctor_name, approved):
    if approved:
        subject = 'Your document update was approved'
        body = (
            f'Hi Dr. {doctor_name},\n\nYour document update request (resume / license) has been '
            'approved and your profile is now up to date.'
        )
    else:
        subject = 'Update on your document request'
        body = (
            f'Hi Dr. {doctor_name},\n\nAfter review, your document update request (resume / '
            'license) was not approved. Your current documents remain in place.'
        )
    _send(doctor_email, subject, body)
