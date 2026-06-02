import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from appointments.models import Appointment
from doctors.models import DoctorProfile
from payments.models import Payment


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture(autouse=True)
def force_paypal_demo(monkeypatch):
    """Keep tests offline + deterministic even if a local .env has real creds."""
    monkeypatch.setattr('payments.paypal.PAYPAL_CLIENT_ID', '')
    monkeypatch.setattr('payments.paypal.PAYPAL_CLIENT_SECRET', '')


def setup_appointment(rate='100.00'):
    patient = User.objects.create_user(
        email='pat@test.com',
        password='patient123',
        role=User.Role.PATIENT,
        status=User.Status.APPROVED,
    )
    du = User.objects.create_user(
        email='doc@test.com',
        password='doctor123',
        role=User.Role.DOCTOR,
        status=User.Status.APPROVED,
    )
    doctor = DoctorProfile.objects.create(user=du, hourly_rate=Decimal(rate))
    appt = Appointment.objects.create(
        patient=patient, doctor=doctor, date=datetime.date.today(), time=datetime.time(10, 0)
    )
    return patient, doctor, appt


@pytest.mark.django_db
def test_create_then_capture_marks_paid(api):
    patient, doctor, appt = setup_appointment()
    api.force_authenticate(patient)

    created = api.post('/api/v1/payments/create/', {'appointment': appt.id}, format='json')
    assert created.status_code == 201
    # No PayPal creds in CI -> the gateway runs the offline DEMO flow.
    assert created.data['demo'] is True
    assert created.data['paypal_order_id'].startswith('DEMO-')
    payment_id = created.data['id']

    captured = api.post(f'/api/v1/payments/{payment_id}/capture/')
    assert captured.status_code == 200
    assert captured.data['status'] == Payment.Status.PAID

    appt.refresh_from_db()
    assert appt.paid is True
    assert str(appt.amount_paid) == '100.00'


def test_fake_capture_still_requires_buyer_approval(monkeypatch):
    """PAYPAL_FAKE_CAPTURE bypasses the money-capture, NOT the approval gate.

    Returning to the page without approving on PayPal must not mark a payment
    paid: capture refuses unless the order is APPROVED/COMPLETED on PayPal.
    """
    from payments import paypal

    monkeypatch.setattr(paypal, 'PAYPAL_CLIENT_ID', 'id')
    monkeypatch.setattr(paypal, 'PAYPAL_CLIENT_SECRET', 'secret')
    monkeypatch.setattr(paypal, 'PAYPAL_FAKE_CAPTURE', True)

    # Buyer never approved -> order still CREATED -> capture must refuse.
    monkeypatch.setattr(paypal, 'get_order', lambda _id: {'status': 'CREATED'})
    with pytest.raises(paypal.PayPalError):
        paypal.capture_order('ORDER-1')

    # Buyer approved on PayPal -> the fake capture completes.
    monkeypatch.setattr(paypal, 'get_order', lambda _id: {'status': 'APPROVED'})
    assert paypal.capture_order('ORDER-1')['status'] == 'COMPLETED'


@pytest.mark.django_db
def test_cannot_pay_someone_elses_appointment(api):
    _, _, appt = setup_appointment()
    intruder = User.objects.create_user(
        email='intruder@test.com',
        password='patient123',
        role=User.Role.PATIENT,
        status=User.Status.APPROVED,
    )
    api.force_authenticate(intruder)
    r = api.post('/api/v1/payments/create/', {'appointment': appt.id}, format='json')
    assert r.status_code == 403
