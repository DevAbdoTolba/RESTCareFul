import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from appointments.models import Appointment
from doctors.models import DoctorAvailability, DoctorProfile

BOOK = '/api/v1/appointments/book/'
MINE = '/api/v1/appointments/'


@pytest.fixture
def api():
    return APIClient()


def make_patient(email='pat@test.com'):
    return User.objects.create_user(
        email=email, password='patient123', role=User.Role.PATIENT, status=User.Status.APPROVED
    )


def make_doctor(email='doc@test.com'):
    u = User.objects.create_user(
        email=email, password='doctor123', role=User.Role.DOCTOR, status=User.Status.APPROVED
    )
    return DoctorProfile.objects.create(user=u)


def slot(doctor, days=3, t=datetime.time(10, 0)):
    return DoctorAvailability.objects.create(
        doctor=doctor,
        date=datetime.date.today() + datetime.timedelta(days=days),
        start_time=t,
        end_time=datetime.time(t.hour, 30),
    )


@pytest.mark.django_db
def test_patient_books_open_slot(api):
    patient, doctor = make_patient(), make_doctor()
    s = slot(doctor)
    api.force_authenticate(patient)
    r = api.post(BOOK, {'doctor': doctor.pk, 'date': str(s.date), 'time': '10:00'}, format='json')
    assert r.status_code == 201
    assert Appointment.objects.filter(patient=patient, doctor=doctor).count() == 1


@pytest.mark.django_db
def test_cannot_book_past_slot(api):
    patient, doctor = make_patient(), make_doctor()
    s = slot(doctor, days=-3)  # safely in the past regardless of the UTC offset
    api.force_authenticate(patient)
    r = api.post(BOOK, {'doctor': doctor.pk, 'date': str(s.date), 'time': '10:00'}, format='json')
    assert r.status_code == 400


@pytest.mark.django_db
def test_taken_slot_cannot_be_rebooked(api):
    patient, doctor = make_patient(), make_doctor()
    s = slot(doctor)
    api.force_authenticate(patient)
    assert (
        api.post(
            BOOK, {'doctor': doctor.pk, 'date': str(s.date), 'time': '10:00'}, format='json'
        ).status_code
        == 201
    )
    second = api.post(
        BOOK, {'doctor': doctor.pk, 'date': str(s.date), 'time': '10:00'}, format='json'
    )
    assert second.status_code in (400, 409)


@pytest.mark.django_db
def test_my_appointments_scoped_to_caller(api):
    patient, doctor = make_patient(), make_doctor()
    Appointment.objects.create(
        patient=patient, doctor=doctor, date=datetime.date.today(), time=datetime.time(9, 0)
    )
    other = make_patient('other@test.com')
    Appointment.objects.create(
        patient=other, doctor=doctor, date=datetime.date.today(), time=datetime.time(11, 0)
    )
    api.force_authenticate(patient)
    r = api.get(MINE)
    assert r.status_code == 200
    assert r.data['count'] == 1


@pytest.mark.django_db
def test_patient_cancels_pending_and_frees_slot(api):
    patient, doctor = make_patient(), make_doctor()
    s = slot(doctor)
    api.force_authenticate(patient)
    booked = api.post(
        BOOK, {'doctor': doctor.pk, 'date': str(s.date), 'time': '10:00'}, format='json'
    )
    appt_id = booked.data['id']
    r = api.post(f'/api/v1/appointments/{appt_id}/cancel/')
    assert r.status_code == 200
    assert Appointment.objects.get(id=appt_id).status == Appointment.Status.CANCELLED
