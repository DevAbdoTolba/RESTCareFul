import pytest
from rest_framework.test import APIClient

from accounts.models import User

SETTINGS = '/api/v1/settings/'


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.django_db
def test_theme_is_public_and_defaults(api):
    r = api.get(SETTINGS)
    assert r.status_code == 200
    assert r.data['theme'] == 'default'


@pytest.mark.django_db
def test_admin_sets_theme_for_everyone(api):
    admin = User.objects.create_superuser(email='admin@test.com', password='admin1234')
    api.force_authenticate(admin)
    put = api.put(SETTINGS, {'theme': 'glass'}, format='json')
    assert put.status_code == 200
    assert put.data['theme'] == 'glass'

    # A different, anonymous visitor now reads the admin's choice.
    anon = APIClient()
    assert anon.get(SETTINGS).data['theme'] == 'glass'


@pytest.mark.django_db
def test_non_admin_cannot_change_theme(api):
    patient = User.objects.create_user(
        email='p@test.com', password='patient123', role=User.Role.PATIENT,
        status=User.Status.APPROVED,
    )
    api.force_authenticate(patient)
    r = api.put(SETTINGS, {'theme': 'glass'}, format='json')
    assert r.status_code == 403
