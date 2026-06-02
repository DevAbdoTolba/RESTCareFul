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
def test_cannot_book_a_half_hour_slot(api):
    """Only on-the-hour appointments are allowed — 09:30 is rejected, 09:00 isn't."""
    patient, doctor = make_patient(), make_doctor()
    d = datetime.date.today() + datetime.timedelta(days=3)
    DoctorAvailability.objects.create(
        doctor=doctor, date=d, start_time=datetime.time(9, 0), end_time=datetime.time(17, 0)
    )
    api.force_authenticate(patient)
    bad = api.post(BOOK, {'doctor': doctor.pk, 'date': str(d), 'time': '09:30'}, format='json')
    assert bad.status_code == 400
    good = api.post(BOOK, {'doctor': doctor.pk, 'date': str(d), 'time': '09:00'}, format='json')
    assert good.status_code == 201


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
def test_patient_cannot_double_book_the_same_time(api):
    """A patient can't hold two appointments at the same date+time — even with
    two different doctors, and the clash is rejected before any payment."""
    patient = make_patient()
    doc_a, doc_b = make_doctor('doca@test.com'), make_doctor('docb@test.com')
    sa, sb = slot(doc_a), slot(doc_b)  # same day, same 10:00 time, different doctors
    api.force_authenticate(patient)

    first = api.post(BOOK, {'doctor': doc_a.pk, 'date': str(sa.date), 'time': '10:00'}, format='json')
    assert first.status_code == 201
    second = api.post(BOOK, {'doctor': doc_b.pk, 'date': str(sb.date), 'time': '10:00'}, format='json')
    assert second.status_code == 409


@pytest.mark.django_db
def test_doctor_cannot_be_double_booked_at_the_same_time(api):
    """Two different patients can't take the same doctor's exact slot."""
    doctor = make_doctor()
    p1, p2 = make_patient('p1@test.com'), make_patient('p2@test.com')
    s = slot(doctor)

    api.force_authenticate(p1)
    assert (
        api.post(BOOK, {'doctor': doctor.pk, 'date': str(s.date), 'time': '10:00'}, format='json').status_code
        == 201
    )
    api.force_authenticate(p2)
    clash = api.post(BOOK, {'doctor': doctor.pk, 'date': str(s.date), 'time': '10:00'}, format='json')
    assert clash.status_code == 409


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
def test_overdue_unconfirmed_appointment_is_expired_and_payment_revoked():
    """A PENDING booking whose time has passed -> OUTDATED, money revoked."""
    from decimal import Decimal

    from appointments.services import expire_overdue_appointments
    from payments.models import Payment

    patient, doctor = make_patient(), make_doctor()
    appt = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        date=datetime.date.today() - datetime.timedelta(days=2),
        time=datetime.time(10, 0),
        status=Appointment.Status.PENDING,
        paid=True,
        amount_paid=Decimal('100.00'),
    )
    payment = Payment.objects.create(
        patient=patient,
        doctor=doctor,
        appointment=appt,
        amount=Decimal('100.00'),
        status=Payment.Status.PAID,
    )

    assert expire_overdue_appointments() == 1

    appt.refresh_from_db()
    payment.refresh_from_db()
    assert appt.status == Appointment.Status.OUTDATED
    assert appt.paid is False
    assert payment.status == Payment.Status.REFUNDED


@pytest.mark.django_db
def test_confirmed_overdue_appointment_is_left_alone():
    """Only unconfirmed (PENDING) bookings expire — a CONFIRMED past visit stays."""
    from appointments.services import expire_overdue_appointments

    patient, doctor = make_patient(), make_doctor()
    appt = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        date=datetime.date.today() - datetime.timedelta(days=2),
        time=datetime.time(10, 0),
        status=Appointment.Status.CONFIRMED,
    )
    assert expire_overdue_appointments() == 0
    appt.refresh_from_db()
    assert appt.status == Appointment.Status.CONFIRMED


@pytest.mark.django_db
def test_display_status_is_unpaid_until_paid_then_pending(api):
    patient, doctor = make_patient(), make_doctor()
    appt = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        date=datetime.date.today() + datetime.timedelta(days=3),
        time=datetime.time(10, 0),
        status=Appointment.Status.PENDING,
        paid=False,
    )
    api.force_authenticate(patient)
    row = api.get(MINE).data['results'][0]
    assert row['status'] == 'pending'
    assert row['display_status'] == 'unpaid'

    appt.paid = True
    appt.save(update_fields=['paid'])
    row = api.get(MINE).data['results'][0]
    assert row['display_status'] == 'pending'


@pytest.mark.django_db
def test_doctor_cannot_manage_an_outdated_appointment(api):
    """An outdated booking is frozen — not even cancel is allowed."""
    patient, doctor = make_patient(), make_doctor()
    appt = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        date=datetime.date.today() - datetime.timedelta(days=3),
        time=datetime.time(10, 0),
        status=Appointment.Status.OUTDATED,
    )
    api.force_authenticate(doctor.user)
    for target in ('confirmed', 'completed', 'cancelled'):
        r = api.post(
            f'/api/v1/appointments/{appt.id}/manage/', {'status': target}, format='json'
        )
        assert r.status_code == 400


@pytest.mark.django_db
def test_doctor_cannot_confirm_an_unpaid_appointment(api):
    patient, doctor = make_patient(), make_doctor()
    appt = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        date=datetime.date.today() + datetime.timedelta(days=3),
        time=datetime.time(10, 0),
        status=Appointment.Status.PENDING,
        paid=False,
    )
    api.force_authenticate(doctor.user)
    manage = f'/api/v1/appointments/{appt.id}/manage/'

    blocked = api.post(manage, {'status': 'confirmed'}, format='json')
    assert blocked.status_code == 400

    appt.paid = True
    appt.save(update_fields=['paid'])
    ok = api.post(manage, {'status': 'confirmed'}, format='json')
    assert ok.status_code == 200
    assert ok.data['status'] == 'confirmed'


@pytest.mark.django_db
def test_cancelling_a_paid_appointment_refunds_the_money(api):
    """Cancelling gives the money back: payment REFUNDED, appointment unpaid."""
    from decimal import Decimal

    from payments.models import Payment

    patient, doctor = make_patient(), make_doctor()
    s = slot(doctor)
    api.force_authenticate(patient)
    appt_id = api.post(
        BOOK, {'doctor': doctor.pk, 'date': str(s.date), 'time': '10:00'}, format='json'
    ).data['id']

    appt = Appointment.objects.get(id=appt_id)
    appt.paid = True
    appt.amount_paid = Decimal('100.00')
    appt.save(update_fields=['paid', 'amount_paid'])
    payment = Payment.objects.create(
        appointment=appt,
        patient=patient,
        doctor=doctor,
        amount=Decimal('100.00'),
        status=Payment.Status.PAID,
    )

    r = api.post(f'/api/v1/appointments/{appt_id}/cancel/')
    assert r.status_code == 200

    appt.refresh_from_db()
    payment.refresh_from_db()
    assert appt.status == Appointment.Status.CANCELLED
    assert appt.paid is False
    assert payment.status == Payment.Status.REFUNDED


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
