"""
Baseline tests for the auth contract.

Doubles as the reference example for the team: pytest-django style,
`@pytest.mark.django_db` for DB access, DRF's APIClient for JSON requests.
Copy this shape into your own slice's tests/.
"""

import pytest
from rest_framework.test import APIClient

from accounts.models import User

REGISTER = '/api/v1/auth/register/'
LOGIN = '/api/v1/auth/login/'
ME = '/api/v1/auth/me/'


@pytest.fixture
def api():
    return APIClient()


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
