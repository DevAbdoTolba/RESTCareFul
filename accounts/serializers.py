"""Serializers for the public auth endpoints."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


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
    """The "who am I" payload — safe to ship to the frontend."""

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
        )
        read_only_fields = fields  # /me is read-only; profile updates have their own endpoint


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


class ChangePasswordSerializer(serializers.Serializer):
    """POST /auth/me/password/ — verify the old password before swapping it."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate_old_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value
