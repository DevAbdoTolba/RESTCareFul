import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from appointments.models import Appointment
from doctors.models import DoctorProfile
from ratings.models import Rating


@pytest.fixture
def api():
    return APIClient()


def completed_appointment(status=Appointment.Status.COMPLETED):
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
    doctor = DoctorProfile.objects.create(user=du)
    appt = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        date=datetime.date.today(),
        time=datetime.time(10, 0),
        status=status,
    )
    return patient, doctor, appt


@pytest.mark.django_db
def test_patient_rates_completed_visit(api):
    patient, doctor, appt = completed_appointment()
    api.force_authenticate(patient)
    r = api.post(
        '/api/v1/ratings/', {'appointment': appt.id, 'stars': 5, 'comment': 'great'}, format='json'
    )
    assert r.status_code == 201
    assert Rating.objects.filter(appointment=appt, stars=5).exists()


@pytest.mark.django_db
def test_cannot_rate_uncompleted_visit(api):
    patient, doctor, appt = completed_appointment(status=Appointment.Status.PENDING)
    api.force_authenticate(patient)
    r = api.post('/api/v1/ratings/', {'appointment': appt.id, 'stars': 4}, format='json')
    assert r.status_code == 400


@pytest.mark.django_db
def test_cannot_rate_twice(api):
    patient, doctor, appt = completed_appointment()
    Rating.objects.create(appointment=appt, patient=patient, doctor=doctor, stars=3)
    api.force_authenticate(patient)
    r = api.post('/api/v1/ratings/', {'appointment': appt.id, 'stars': 5}, format='json')
    assert r.status_code == 400


@pytest.mark.django_db
def test_doctor_rating_summary(api):
    patient, doctor, appt = completed_appointment()
    Rating.objects.create(appointment=appt, patient=patient, doctor=doctor, stars=4)
    api.force_authenticate(patient)
    r = api.get(f'/api/v1/ratings/doctor/{doctor.pk}/')
    assert r.status_code == 200
    assert r.data['count'] == 1
    assert r.data['average'] == 4.0
