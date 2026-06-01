import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from doctors.models import DocUpdateRequest, DoctorAvailability, DoctorProfile


@pytest.fixture
def api():
    return APIClient()


def make_doctor(email='doc@test.com', status=User.Status.APPROVED):
    u = User.objects.create_user(
        email=email, password='doctor123', role=User.Role.DOCTOR, status=status,
        first_name='Dr', last_name='Who',
    )
    return DoctorProfile.objects.create(user=u)


@pytest.mark.django_db
def test_only_approved_doctors_are_listed(api):
    make_doctor('ok@test.com', status=User.Status.APPROVED)
    make_doctor('pending@test.com', status=User.Status.PENDING)
    patient = User.objects.create_user(
        email='p@test.com', password='patient123', role=User.Role.PATIENT, status=User.Status.APPROVED
    )
    api.force_authenticate(patient)
    r = api.get('/api/v1/doctors/')
    assert r.status_code == 200
    assert r.data['count'] == 1


@pytest.mark.django_db
def test_doctor_upserts_own_profile(api):
    prof = make_doctor()
    api.force_authenticate(prof.user)
    r = api.put('/api/v1/doctors/me/', {'hourly_rate': '50.00'}, format='json')
    assert r.status_code == 200
    prof.refresh_from_db()
    assert str(prof.hourly_rate) == '50.00'


@pytest.mark.django_db
def test_open_slots_hide_past_windows(api):
    prof = make_doctor()
    DoctorAvailability.objects.create(
        doctor=prof, date=datetime.date.today() - datetime.timedelta(days=2),
        start_time=datetime.time(9, 0), end_time=datetime.time(9, 30),
    )
    DoctorAvailability.objects.create(
        doctor=prof, date=datetime.date.today() + datetime.timedelta(days=2),
        start_time=datetime.time(9, 0), end_time=datetime.time(9, 30),
    )
    patient = User.objects.create_user(
        email='p@test.com', password='patient123', role=User.Role.PATIENT, status=User.Status.APPROVED
    )
    api.force_authenticate(patient)
    r = api.get(f'/api/v1/doctors/{prof.pk}/availability/')
    assert r.status_code == 200
    assert r.data['count'] == 1  # only the future window


@pytest.mark.django_db
def test_update_request_approved_patches_profile(api):
    prof = make_doctor()
    req = DocUpdateRequest.objects.create(
        doctor=prof, doctor_name='Dr Who', license_url='https://new-license'
    )
    admin = User.objects.create_superuser(email='admin@test.com', password='admin1234')
    api.force_authenticate(admin)
    r = api.post(f'/api/v1/doctors/update-requests/{req.id}/approve/')
    assert r.status_code == 200
    prof.refresh_from_db()
    assert prof.license_url == 'https://new-license'
