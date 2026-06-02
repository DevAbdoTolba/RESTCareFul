"""Serializers for the public auth endpoints."""

import re

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

User = get_user_model()

# Oldest plausible birth year — guards against typos like year 0900 or 3000.
MAX_AGE_YEARS = 120

# Digits, spaces, +, -, parens and a leading +; the digit-count is checked too.
PHONE_RE = re.compile(r'^\+?[0-9\s\-()]+$')


def validate_dob(value):
    """A date of birth must be a real past date — never in the future."""
    if value is None:
        return value
    today = timezone.now().date()
    if value > today:
        raise serializers.ValidationError('Date of birth cannot be in the future.')
    if value.year < today.year - MAX_AGE_YEARS:
        raise serializers.ValidationError('Please enter a valid date of birth.')
    return value


def validate_phone(value):
    """A phone number must be 7–15 digits, optionally with + / spaces / dashes."""
    if not value:
        return value
    digits = sum(ch.isdigit() for ch in value)
    if not PHONE_RE.match(value) or not (7 <= digits <= 15):
        raise serializers.ValidationError('Enter a valid phone number (7–15 digits).')
    return value


class RegisterSerializer(serializers.ModelSerializer):
    """
    Self-service signup. Only patients and doctors register through here —
    admins are created via `manage.py createsuperuser` or the Django admin.

    Patients auto-approve; doctors land as `pending` and wait for the admin's
    review (and a DoctorProfile, owned by the `doctors` app).
    """

    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'password',
            'role',
            'first_name',
            'last_name',
            'phone_number',
            'gender',
            'date_of_birth',
            'description',
        )
        read_only_fields = ('id',)

    def validate_role(self, value):
        if value == User.Role.ADMIN:
            raise serializers.ValidationError('Admins cannot self-register.')
        return value

    def validate_date_of_birth(self, value):
        return validate_dob(value)

    def validate_phone_number(self, value):
        return validate_phone(value)

    def create(self, validated_data):
        # Patients are trusted instantly; doctors wait for an admin to verify
        # their license/resume before they can be booked.
        role = validated_data.get('role', User.Role.PATIENT)
        validated_data['status'] = (
            User.Status.PENDING if role == User.Role.DOCTOR else User.Status.APPROVED
        )
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)


class UserSerializer(serializers.ModelSerializer):
    """The "who am I" payload — safe to ship to the frontend.

    For doctors we flatten the DoctorProfile fields onto the payload so the
    profile page can show their own specialty, rate and (importantly) their
    resume + license without a second request.
    """

    specialty_id = serializers.SerializerMethodField()
    hourly_rate = serializers.SerializerMethodField()
    resume_url = serializers.SerializerMethodField()
    license_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'role',
            'status',
            'first_name',
            'last_name',
            'phone_number',
            'gender',
            'date_of_birth',
            'description',
            'created_at',
            'updated_at',
            'specialty_id',
            'hourly_rate',
            'resume_url',
            'license_url',
        )
        # /me is read-only; profile updates have their own endpoint. (Only the
        # model fields go here — the method fields above are read-only already.)
        read_only_fields = (
            'id',
            'email',
            'role',
            'status',
            'first_name',
            'last_name',
            'phone_number',
            'gender',
            'date_of_birth',
            'description',
            'created_at',
            'updated_at',
        )

    def _profile(self, obj):
        if obj.role != User.Role.DOCTOR:
            return None
        return getattr(obj, 'doctor_profile', None)

    def get_specialty_id(self, obj):
        prof = self._profile(obj)
        return prof.specialty_id if prof else None

    def get_hourly_rate(self, obj):
        prof = self._profile(obj)
        return str(prof.hourly_rate) if prof and prof.hourly_rate is not None else None

    def get_resume_url(self, obj):
        prof = self._profile(obj)
        return prof.resume_url if prof else None

    def get_license_url(self, obj):
        prof = self._profile(obj)
        return prof.license_url if prof else None


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """PATCH /auth/me/profile/ — the fields a user may edit about themselves.

    Deliberately excludes role/status/email so a patient can't promote
    themselves or jump the doctor approval queue from the profile form.
    """

    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'phone_number',
            'gender',
            'date_of_birth',
            'description',
        )

    def validate_date_of_birth(self, value):
        return validate_dob(value)

    def validate_phone_number(self, value):
        return validate_phone(value)


class ChangePasswordSerializer(serializers.Serializer):
    """POST /auth/me/password/ — verify the old password before swapping it."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate_old_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value
