"""
Baseline tests for the auth contract.

Doubles as the reference example for the team: pytest-django style,
`@pytest.mark.django_db` for DB access, DRF's APIClient for JSON requests.
Copy this shape into your own slice's tests/.
"""

import datetime

import pytest
from django.core import mail
from rest_framework.test import APIClient

from accounts.models import User

REGISTER = '/api/v1/auth/register/'
LOGIN = '/api/v1/auth/login/'
ME = '/api/v1/auth/me/'


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.django_db
def test_register_sends_a_welcome_email(api):
    mail.outbox.clear()
    api.post(
        REGISTER,
        {'email': 'pat@test.com', 'password': 'patient123', 'role': 'patient', 'first_name': 'Pat'},
        format='json',
    )
    assert any('pat@test.com' in m.to and 'Welcome' in m.subject for m in mail.outbox)


@pytest.mark.django_db
def test_register_rejects_a_future_date_of_birth(api):
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    r = api.post(
        REGISTER,
        {
            'email': 'future@test.com',
            'password': 'patient123',
            'role': 'patient',
            'first_name': 'Future',
            'date_of_birth': str(tomorrow),
        },
        format='json',
    )
    assert r.status_code == 400
    assert 'date_of_birth' in r.data
    assert not User.objects.filter(email='future@test.com').exists()


@pytest.mark.django_db
def test_register_patient_is_auto_approved(api):
    r = api.post(
        REGISTER,
        {'email': 'pat@test.com', 'password': 'patient123', 'role': 'patient', 'first_name': 'Pat'},
        format='json',
    )
    assert r.status_code == 201
    assert User.objects.get(email='pat@test.com').status == User.Status.APPROVED


@pytest.mark.django_db
def test_register_doctor_is_pending(api):
    r = api.post(
        REGISTER,
        {'email': 'doc@test.com', 'password': 'doctor123', 'role': 'doctor', 'first_name': 'Doc'},
        format='json',
    )
    assert r.status_code == 201
    assert User.objects.get(email='doc@test.com').status == User.Status.PENDING


@pytest.mark.django_db
def test_cannot_self_register_as_admin(api):
    r = api.post(
        REGISTER,
        {'email': 'evil@test.com', 'password': 'admin1234', 'role': 'admin'},
        format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_duplicate_email_is_rejected(api):
    User.objects.create_user(email='dupe@test.com', password='secret123')
    r = api.post(
        REGISTER,
        {'email': 'dupe@test.com', 'password': 'secret123', 'role': 'patient'},
        format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_login_returns_access_and_refresh(api):
    User.objects.create_user(email='u@test.com', password='secret123', status=User.Status.APPROVED)
    r = api.post(LOGIN, {'email': 'u@test.com', 'password': 'secret123'}, format='json')
    assert r.status_code == 200
    assert 'access' in r.data
    assert 'refresh' in r.data


@pytest.mark.django_db
def test_login_with_wrong_password_is_unauthorized(api):
    User.objects.create_user(email='u@test.com', password='secret123', status=User.Status.APPROVED)
    r = api.post(LOGIN, {'email': 'u@test.com', 'password': 'WRONG'}, format='json')
    assert r.status_code == 401


@pytest.mark.django_db
def test_me_requires_authentication(api):
    assert api.get(ME).status_code == 401


@pytest.mark.django_db
def test_me_returns_the_current_user(api):
    User.objects.create_user(email='u@test.com', password='secret123', status=User.Status.APPROVED)
    login = api.post(LOGIN, {'email': 'u@test.com', 'password': 'secret123'}, format='json')
    api.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
    r = api.get(ME)
    assert r.status_code == 200
    assert r.data['email'] == 'u@test.com'


@pytest.mark.django_db
def test_me_carries_the_doctors_own_documents(api):
    """A doctor's /me payload includes their resume + license so they can see
    their own papers on the profile page."""
    from doctors.models import DoctorProfile

    doc = User.objects.create_user(
        email='doc@test.com',
        password='doctor123',
        role=User.Role.DOCTOR,
        status=User.Status.APPROVED,
    )
    DoctorProfile.objects.create(
        user=doc, resume_url='https://example.com/r.png', license_url='https://example.com/l.png'
    )
    api.force_authenticate(doc)
    r = api.get(ME)
    assert r.status_code == 200
    assert r.data['resume_url'] == 'https://example.com/r.png'
    assert r.data['license_url'] == 'https://example.com/l.png'


@pytest.mark.django_db
def test_admin_approves_a_pending_doctor(api):
    admin = User.objects.create_superuser(email='admin@test.com', password='admin1234')
    doctor = User.objects.create_user(
        email='doc@test.com',
        password='doctor123',
        role=User.Role.DOCTOR,
        status=User.Status.PENDING,
    )
    api.force_authenticate(admin)
    r = api.post(f'/api/v1/auth/admin/doctors/{doctor.id}/approve/')
    assert r.status_code == 200
    doctor.refresh_from_db()
    assert doctor.status == User.Status.APPROVED


@pytest.mark.django_db
def test_non_admin_cannot_approve_doctors(api):
    patient = User.objects.create_user(
        email='p@test.com',
        password='patient123',
        role=User.Role.PATIENT,
        status=User.Status.APPROVED,
    )
    doctor = User.objects.create_user(
        email='doc@test.com',
        password='doctor123',
        role=User.Role.DOCTOR,
        status=User.Status.PENDING,
    )
    api.force_authenticate(patient)
    assert api.post(f'/api/v1/auth/admin/doctors/{doctor.id}/approve/').status_code == 403


@pytest.mark.django_db
def test_change_password_requires_correct_old_one(api):
    user = User.objects.create_user(
        email='u@test.com', password='secret123', status=User.Status.APPROVED
    )
    api.force_authenticate(user)
    bad = api.post(
        '/api/v1/auth/me/password/',
        {'old_password': 'WRONG', 'new_password': 'brandnew1'},
        format='json',
    )
    assert bad.status_code == 400
    ok = api.post(
        '/api/v1/auth/me/password/',
        {'old_password': 'secret123', 'new_password': 'brandnew1'},
        format='json',
    )
    assert ok.status_code == 200
    user.refresh_from_db()
    assert user.check_password('brandnew1')


@pytest.mark.django_db
def test_profile_update_cannot_change_role(api):
    user = User.objects.create_user(
        email='u@test.com',
        password='secret123',
        role=User.Role.PATIENT,
        status=User.Status.APPROVED,
    )
    api.force_authenticate(user)
    r = api.patch('/api/v1/auth/me/profile/', {'first_name': 'New', 'role': 'admin'}, format='json')
    assert r.status_code == 200
    user.refresh_from_db()
    assert user.first_name == 'New'
    assert user.role == User.Role.PATIENT  # role is not an editable profile field


@pytest.mark.django_db
def test_admin_can_ban_user_and_login_is_blocked(api):
    admin = User.objects.create_superuser(email='admin@test.com', password='admin1234')
    patient = User.objects.create_user(
        email='p@test.com',
        password='patient123',
        role=User.Role.PATIENT,
        status=User.Status.APPROVED,
    )
    api.force_authenticate(admin)
    r = api.post(f'/api/v1/auth/admin/users/{patient.id}/ban/')
    assert r.status_code == 200
    patient.refresh_from_db()
    assert patient.status == User.Status.BANNED
    assert patient.is_active is False
    # A banned account can't obtain a token.
    assert (
        APIClient()
        .post(LOGIN, {'email': 'p@test.com', 'password': 'patient123'}, format='json')
        .status_code
        == 401
    )


@pytest.mark.django_db
def test_admins_cannot_be_banned(api):
    admin = User.objects.create_superuser(email='admin@test.com', password='admin1234')
    other = User.objects.create_user(
        email='a2@test.com', password='admin1234', role=User.Role.ADMIN, status=User.Status.APPROVED
    )
    api.force_authenticate(admin)
    assert api.post(f'/api/v1/auth/admin/users/{other.id}/ban/').status_code == 400


@pytest.mark.django_db
def test_admin_user_detail_carries_doctor_rating_and_stats(api):
    from doctors.models import DoctorProfile

    admin = User.objects.create_superuser(email='admin@test.com', password='admin1234')
    doc_user = User.objects.create_user(
        email='doc@test.com',
        password='doctor123',
        role=User.Role.DOCTOR,
        status=User.Status.APPROVED,
    )
    DoctorProfile.objects.create(user=doc_user)
    api.force_authenticate(admin)
    r = api.get(f'/api/v1/auth/admin/users/{doc_user.id}/')
    assert r.status_code == 200
    assert 'rating' in r.data and 'stats' in r.data
    assert r.data['stats']['appointments'] == 0
