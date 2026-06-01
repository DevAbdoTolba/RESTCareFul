from django.utils import timezone
from rest_framework import serializers

from doctors.models import DoctorAvailability

from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    """Read shape shared by patient and doctor history lists."""

    doctor_id = serializers.IntegerField(read_only=True)
    doctor_name = serializers.SerializerMethodField()
    doctor_specialty = serializers.CharField(
        source='doctor.specialty.name', read_only=True, default=None
    )
    patient_id = serializers.IntegerField(read_only=True)
    patient_name = serializers.SerializerMethodField()
    patient_email = serializers.EmailField(source='patient.email', read_only=True)

    class Meta:
        model = Appointment
        fields = (
            'id',
            'date',
            'time',
            'status',
            'notes',
            'paid',
            'amount_paid',
            'doctor_id',
            'doctor_name',
            'doctor_specialty',
            'patient_id',
            'patient_name',
            'patient_email',
            'created_at',
        )

    def _full_name(self, user):
        return f'{user.first_name} {user.last_name}'.strip() or user.email

    def get_doctor_name(self, obj):
        return self._full_name(obj.doctor.user)

    def get_patient_name(self, obj):
        return self._full_name(obj.patient)


class BookAppointmentSerializer(serializers.Serializer):
    """Patient books by picking one of a doctor's open availability windows."""

    availability = serializers.PrimaryKeyRelatedField(queryset=DoctorAvailability.objects.all())
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_availability(self, slot):
        if not slot.is_available:
            raise serializers.ValidationError('That slot is already taken.')
        if slot.date < timezone.now().date():
            raise serializers.ValidationError('Cannot book a slot in the past.')
        return slot
