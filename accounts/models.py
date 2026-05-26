"""
Custom User model — the foundation everyone else depends on.

Two things make this non-default:
  1. **Email is the login field** (no `username`). Matches the React app's
     register/login UX where users type an email + password.
  2. **`role` + `status` ENUMS** sit directly on the user. Patients/admins are
     stored only here; doctors get an extra `Doctor` row via the OneToOneField
     subtype in the `doctors` app (ISA pattern — see docs/ARCHITECTURE.md).

Defining this BEFORE any other migrations run is mandatory — swapping
AUTH_USER_MODEL after the fact is famously painful in Django.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager that creates users by email instead of username."""

    use_in_migrations = True

    def _create(self, email, password, **extra_fields):
        if not email:
            raise ValueError('An email address is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # Superusers are the admin role and skip the approval gate.
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('status', User.Status.APPROVED)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create(email, password, **extra_fields)


class User(AbstractUser):
    """The one User table for every role. Doctor-specific fields live on Doctor."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        DOCTOR = 'doctor', 'Doctor'
        PATIENT = 'patient', 'Patient'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    class Gender(models.TextChoices):
        FEMALE = 'female', 'Female'
        MALE = 'male', 'Male'
        OTHER = 'other', 'Other'

    # Replace username-based auth with email-based.
    username = None
    email = models.EmailField(unique=True)

    # Domain fields shared by every role.
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PATIENT)
    # Default = pending so we fail closed — patient/admin flows must explicitly approve.
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    phone_number = models.CharField(max_length=32, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # email is USERNAME_FIELD; password is prompted separately

    objects = UserManager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.email} ({self.role})'
