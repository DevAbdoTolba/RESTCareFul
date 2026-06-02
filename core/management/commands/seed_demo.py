"""
Demo-data seeder — the Django way (a management command using the ORM).

    python manage.py seed_demo            # seed once (no-op if already seeded)
    python manage.py seed_demo --flush    # wipe demo rows, then reseed

Why a command and not a fixture: users need real hashed passwords (create_user),
the Doctor ISA row hangs off the User PK, and appointment/availability dates have
to be relative to *today* so future slots are actually bookable — all of which
are awkward in a static fixture but trivial through the ORM.

Demo accounts mirror the React app's seed so the same logins work end-to-end:
  admin@usecare.test / admin123      (admin)
  <name>@usecare.test / doctor123    (doctors)
  <name>@usecare.test / patient123   (patients)
"""

from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment
from doctors.models import DoctorAvailability, DoctorProfile, DocUpdateRequest
from payments.models import Payment
from ratings.models import Rating
from specialties.models import Specialty, SpecialtySuggestion

DEMO_DOMAIN = '@usecare.test'

SPECIALTIES = [
    ('Cardiology', 'Heart and vascular system'),
    ('Pediatrics', 'Care for infants and children'),
    ('Dermatology', 'Skin, hair, nails'),
    ('Neurology', 'Nervous system'),
]

# (email-local, first, last, specialty, hourly_rate, status, gender, dob, about)
DOCTORS = [
    (
        'ahmed',
        'Ahmed',
        'Tolba',
        'Cardiology',
        60,
        'approved',
        'male',
        date(1986, 9, 3),
        '8 yrs cardiology experience',
    ),
    (
        'layla',
        'Layla',
        'Farouk',
        'Cardiology',
        65,
        'approved',
        'female',
        date(1980, 2, 28),
        "Cardiologist, women's heart health focus",
    ),
    (
        'mona',
        'Mona',
        'El-Sayed',
        'Dermatology',
        50,
        'approved',
        'female',
        date(1988, 7, 15),
        'Dermatology specialist',
    ),
    (
        'samir',
        'Samir',
        'Hassan',
        'Pediatrics',
        45,
        'pending',
        'male',
        date(1990, 1, 22),
        'Pediatrician, fellowship at Cairo Univ.',
    ),
    (
        'karim',
        'Karim',
        'Nasr',
        'Neurology',
        75,
        'pending',
        'male',
        date(1982, 11, 30),
        'Neurology, stroke specialist',
    ),
]

# (email-local, first, last, gender, dob)
PATIENTS = [
    ('yara', 'Yara', 'Mostafa', 'female', date(1995, 3, 8)),
    ('omar', 'Omar', 'Hany', 'male', date(1992, 12, 1)),
    ('nour', 'Nour', 'Adel', 'female', date(2001, 5, 19)),
    ('ali', 'Ali', 'Mahmoud', 'male', date(1978, 8, 25)),
    ('hana', 'Hana', 'Khaled', 'female', date(1989, 11, 4)),
    ('tarek', 'Tarek', 'Rashid', 'male', date(1975, 6, 17)),
]

# Real document images (they actually render in the browser, unlike the old
# placeholder .pdf links). Cycled across the doctors.
RESUME_IMAGES = [
    'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSwCx_R8vbYzpGGU1D5Bxl_g5WauSrp3XjmoQ&s',
    'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTAuolFUEaw4XH46pjc0EVp8jQh03jOB-lnmw&s',
    'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQepvILcg7YnMI4wJb4_ec-ULE5gsKUJoFleA&s',
]
LICENSE_IMAGES = [
    'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSf9uu1xXXrErHQ-8V8xm_9S7UxjQPW3lajWA&s',
    'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSW2e507Jg5SZLxdoen9u-e5TcxxXEWpDec0w&s',
    'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSJdqfdR05A-7geVRnEHbrnkA_ClwjxCbN9vg&s',
]


class Command(BaseCommand):
    help = 'Seed the database with relevant demo data (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete existing demo rows before seeding.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['flush']:
            self._flush()

        if User.objects.filter(email=f'admin{DEMO_DOMAIN}').exists():
            self.stdout.write(
                self.style.WARNING('Demo data already present. Re-run with --flush to reset.')
            )
            return

        today = timezone.now().date()

        specialties = self._seed_specialties()
        self._seed_admin()
        doctors = self._seed_doctors(specialties)
        patients = self._seed_patients()
        self._seed_availability(doctors, today)
        self._seed_history(doctors, patients, today)
        self._seed_upcoming(doctors, patients, today)
        self._seed_outdated(doctors, patients, today)
        self._seed_proposals(doctors)

        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded: {len(specialties)} specialties, 1 admin, {len(doctors)} doctors, '
                f'{len(patients)} patients, plus availability, appointments, ratings & payments.'
            )
        )
        self.stdout.write(
            'Logins: admin@usecare.test/admin123 · ahmed@usecare.test/doctor123 · '
            'yara@usecare.test/patient123'
        )

    # --- steps --------------------------------------------------------------

    def _seed_specialties(self):
        out = {}
        for name, desc in SPECIALTIES:
            # get_or_create: a demo specialty may have been kept on flush because
            # a real doctor still references it (see _flush).
            out[name], _ = Specialty.objects.get_or_create(
                name=name, defaults={'description': desc}
            )
        return out

    def _seed_admin(self):
        return User.objects.create_superuser(
            email=f'admin{DEMO_DOMAIN}',
            password='admin123',
            first_name='Sara',
            last_name='Hassan',
            gender=User.Gender.FEMALE,
        )

    def _seed_doctors(self, specialties):
        doctors = {}
        for i, (local, first, last, spec, rate, status, gender, dob, about) in enumerate(DOCTORS):
            user = User.objects.create_user(
                email=f'{local}{DEMO_DOMAIN}',
                password='doctor123',
                role=User.Role.DOCTOR,
                status=status,
                first_name=first,
                last_name=last,
                gender=gender,
                date_of_birth=dob,
                description=about,
                phone_number='+20-100-000-0000',
            )
            profile = DoctorProfile.objects.create(
                user=user,
                specialty=specialties[spec],
                hourly_rate=Decimal(rate),
                resume_url=RESUME_IMAGES[i % len(RESUME_IMAGES)],
                license_url=LICENSE_IMAGES[i % len(LICENSE_IMAGES)],
            )
            doctors[local] = profile
        return doctors

    def _seed_patients(self):
        patients = {}
        for local, first, last, gender, dob in PATIENTS:
            patients[local] = User.objects.create_user(
                email=f'{local}{DEMO_DOMAIN}',
                password='patient123',
                role=User.Role.PATIENT,
                status=User.Status.APPROVED,
                first_name=first,
                last_name=last,
                gender=gender,
                date_of_birth=dob,
                phone_number='+20-100-000-0000',
            )
        return patients

    def _seed_availability(self, doctors, today):
        """Open future windows for the approved doctors (these are bookable)."""
        approved = [d for d in doctors.values() if d.user.status == User.Status.APPROVED]
        for profile in approved:
            for offset in (2, 4, 7, 9, 11):
                DoctorAvailability.objects.create(
                    doctor=profile,
                    date=today + timedelta(days=offset),
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                    is_available=True,
                )

    def _seed_history(self, doctors, patients, today):
        """Past, completed visits — each with a rating + a paid payment."""
        rows = [
            ('ahmed', 'yara', 20, time(9, 0), 5, 'Very thorough, explained everything clearly.'),
            ('ahmed', 'ali', 14, time(10, 0), 4, 'Good visit, a bit of a wait.'),
            ('mona', 'nour', 12, time(11, 0), 5, 'Cleared my skin issue fast.'),
            ('layla', 'hana', 9, time(16, 0), 4, ''),
        ]
        for doc_local, pat_local, days_ago, t, stars, comment in rows:
            profile = doctors[doc_local]
            patient = patients[pat_local]
            amount = profile.hourly_rate or Decimal('0')
            appt = Appointment.objects.create(
                patient=patient,
                doctor=profile,
                date=today - timedelta(days=days_ago),
                time=t,
                status=Appointment.Status.COMPLETED,
                notes='Visit completed.',
                paid=True,
                amount_paid=amount,
            )
            Rating.objects.create(
                appointment=appt,
                patient=patient,
                doctor=profile,
                stars=stars,
                comment=comment,
            )
            Payment.objects.create(
                appointment=appt,
                patient=patient,
                doctor=profile,
                amount=amount,
                status=Payment.Status.PAID,
                paypal_order_id='DEMO-SEEDED',
            )

    def _seed_upcoming(self, doctors, patients, today):
        """Future appointments booked into (and closing) some open windows."""
        rows = [
            ('ahmed', 'omar', 2, Appointment.Status.CONFIRMED),
            ('mona', 'tarek', 4, Appointment.Status.PENDING),
            ('layla', 'yara', 7, Appointment.Status.CONFIRMED),
        ]
        for doc_local, pat_local, offset, status in rows:
            profile = doctors[doc_local]
            slot_date = today + timedelta(days=offset)
            Appointment.objects.create(
                patient=patients[pat_local],
                doctor=profile,
                date=slot_date,
                time=time(9, 0),
                status=status,
                notes='',
            )
            # window stays open; the 09:00 slot is simply excluded by the slots
            # endpoint (which drops already-booked times), the rest stay bookable.

    def _seed_outdated(self, doctors, patients, today):
        """A booking the doctor never confirmed in time: paid, but past + still
        PENDING. The auto-expiry sweep flips it to OUTDATED and refunds the
        payment on the next dashboard/appointments read, so the admin sees the
        revoked money drop out of the totals live."""
        profile = doctors['ahmed']
        patient = patients['nour']
        amount = profile.hourly_rate or Decimal('0')
        appt = Appointment.objects.create(
            patient=patient,
            doctor=profile,
            date=today - timedelta(days=5),
            time=time(13, 0),
            status=Appointment.Status.PENDING,
            paid=True,
            amount_paid=amount,
        )
        Payment.objects.create(
            appointment=appt,
            patient=patient,
            doctor=profile,
            amount=amount,
            status=Payment.Status.PAID,
            paypal_order_id='DEMO-SEEDED',
        )

    def _seed_proposals(self, doctors):
        """A pending specialty suggestion + a pending resume/license update request."""
        SpecialtySuggestion.objects.create(
            name='Orthopedics',
            proposed_by=doctors['samir'].user,
            status=SpecialtySuggestion.Status.PENDING,
        )
        mona = doctors['mona']
        DocUpdateRequest.objects.create(
            doctor=mona,
            doctor_name=f'{mona.user.first_name} {mona.user.last_name}',
            license_url=LICENSE_IMAGES[2],
            status=DocUpdateRequest.Status.PENDING,
        )

    # --- flush --------------------------------------------------------------

    def _flush(self):
        """Delete demo rows in FK-safe order (everything tied to @usecare.test).

        Appointments/payments/ratings are matched by demo patient OR demo
        doctor: a real (non-demo) patient may have booked a demo doctor, and
        those rows PROTECT the DoctorProfile, so they must go first too.
        """
        demo_users = User.objects.filter(email__endswith=DEMO_DOMAIN)
        tied_to_demo = Q(patient__in=demo_users) | Q(doctor__user__in=demo_users)
        Payment.objects.filter(tied_to_demo).delete()
        Rating.objects.filter(tied_to_demo).delete()
        Appointment.objects.filter(tied_to_demo).delete()
        DocUpdateRequest.objects.filter(doctor__user__in=demo_users).delete()
        DoctorAvailability.objects.filter(doctor__user__in=demo_users).delete()
        SpecialtySuggestion.objects.filter(proposed_by__in=demo_users).delete()
        DoctorProfile.objects.filter(user__in=demo_users).delete()
        demo_users.delete()
        # Only drop demo specialties nothing still points at — a real doctor may
        # have picked one (it PROTECTs the row); leave those in place.
        for spec in Specialty.objects.filter(name__in=[n for n, _ in SPECIALTIES]):
            if not spec.doctors.exists():
                spec.delete()
        self.stdout.write(self.style.WARNING('Flushed existing demo data.'))
