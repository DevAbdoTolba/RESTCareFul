import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from appointments.models import Appointment
from doctors.models import DoctorProfile
from payments.models import Payment

METRICS = '/api/v1/dashboard/metrics/'


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.django_db
def test_metrics_require_admin(api):
    patient = User.objects.create_user(
        email='p@test.com',
        password='patient123',
        role=User.Role.PATIENT,
        status=User.Status.APPROVED,
    )
    api.force_authenticate(patient)
    assert api.get(METRICS).status_code == 403


@pytest.mark.django_db
def test_platform_revenue_is_12_percent(api):
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
    doctor = DoctorProfile.objects.create(user=du, hourly_rate=Decimal('100.00'))
    appt = Appointment.objects.create(
        patient=patient, doctor=doctor, date=datetime.date.today(), time=datetime.time(10, 0)
    )
    Payment.objects.create(
        appointment=appt,
        patient=patient,
        doctor=doctor,
        amount=Decimal('100.00'),
        status=Payment.Status.PAID,
    )
    admin = User.objects.create_superuser(email='admin@test.com', password='admin1234')
    api.force_authenticate(admin)
    r = api.get(METRICS)
    assert r.status_code == 200
    assert Decimal(str(r.data['total_paid'])) == Decimal('100.00')
    assert Decimal(str(r.data['platform_revenue'])) == Decimal('12.00')
