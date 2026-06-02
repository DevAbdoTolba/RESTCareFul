import pytest
from django.core import mail
from rest_framework.test import APIClient

from accounts.models import User

SETTINGS = '/api/v1/settings/'


def test_notification_emails_are_sent():
    from core import emails

    mail.outbox.clear()
    emails.notify_account_created('a@b.com', 'Alice')
    emails.notify_account_banned('a@b.com', 'Alice')
    emails.notify_account_unbanned('a@b.com', 'Alice')
    emails.notify_doctor_new_appointment('doc@b.com', 'House', 'Alice', '2026-06-10', '10:00')
    emails.notify_patient_appointment_confirmed('a@b.com', 'Alice', 'House', '2026-06-10', '10:00')
    emails.notify_specialty_decision('doc@b.com', 'House', 'Oncology', approved=True)
    emails.notify_doc_update_decision('doc@b.com', 'House', approved=False)
    assert len(mail.outbox) == 7
    assert any('Welcome' in m.subject for m in mail.outbox)


def test_email_without_recipient_is_a_noop():
    from core import emails

    mail.outbox.clear()
    emails.notify_account_created('', 'Nobody')
    assert mail.outbox == []


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
