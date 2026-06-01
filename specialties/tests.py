import pytest
from rest_framework.test import APIClient

from accounts.models import User
from specialties.models import Specialty, SpecialtySuggestion


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email='admin@test.com', password='admin1234')


@pytest.fixture
def doctor(db):
    return User.objects.create_user(
        email='doc@test.com',
        password='doctor123',
        role=User.Role.DOCTOR,
        status=User.Status.APPROVED,
    )


@pytest.mark.django_db
def test_specialty_list_is_public(api):
    Specialty.objects.create(name='Cardiology')
    r = api.get('/api/v1/specialties/')
    assert r.status_code == 200
    assert len(r.data) == 1


@pytest.mark.django_db
def test_doctor_can_suggest_a_specialty(api, doctor):
    api.force_authenticate(doctor)
    r = api.post('/api/v1/specialties/suggestions/', {'name': 'Neurology'}, format='json')
    assert r.status_code == 201
    assert SpecialtySuggestion.objects.filter(name='Neurology', proposed_by=doctor).exists()


@pytest.mark.django_db
def test_patient_cannot_suggest(api):
    patient = User.objects.create_user(
        email='p@test.com', password='patient123', role=User.Role.PATIENT
    )
    api.force_authenticate(patient)
    r = api.post('/api/v1/specialties/suggestions/', {'name': 'X'}, format='json')
    assert r.status_code == 403


@pytest.mark.django_db
def test_admin_approve_creates_real_specialty(api, admin, doctor):
    s = SpecialtySuggestion.objects.create(name='Dermatology', proposed_by=doctor)
    api.force_authenticate(admin)
    r = api.post(f'/api/v1/specialties/suggestions/{s.id}/approve/')
    assert r.status_code == 200
    assert Specialty.objects.filter(name='Dermatology').exists()
    s.refresh_from_db()
    assert s.status == SpecialtySuggestion.Status.APPROVED
