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


def setup_appointment(rate='100.00'):
    patient = User.objects.create_user(
        email='pat@test.com', password='patient123', role=User.Role.PATIENT, status=User.Status.APPROVED
    )
    du = User.objects.create_user(
        email='doc@test.com', password='doctor123', role=User.Role.DOCTOR, status=User.Status.APPROVED
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
    assert created.data['paypal_order_id'].startswith('ORDER-')
    payment_id = created.data['id']

    captured = api.post(f'/api/v1/payments/{payment_id}/capture/')
    assert captured.status_code == 200
    assert captured.data['status'] == Payment.Status.PAID

    appt.refresh_from_db()
    assert appt.paid is True
    assert str(appt.amount_paid) == '100.00'


@pytest.mark.django_db
def test_cannot_pay_someone_elses_appointment(api):
    _, _, appt = setup_appointment()
    intruder = User.objects.create_user(
        email='intruder@test.com', password='patient123', role=User.Role.PATIENT, status=User.Status.APPROVED
    )
    api.force_authenticate(intruder)
    r = api.post('/api/v1/payments/create/', {'appointment': appt.id}, format='json')
    assert r.status_code == 403
