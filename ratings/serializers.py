from rest_framework import serializers

from appointments.models import Appointment

from .models import Rating


class RatingSerializer(serializers.ModelSerializer):
    appointment_id = serializers.IntegerField(read_only=True)
    doctor_id = serializers.IntegerField(read_only=True)
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = Rating
        fields = (
            'appointment_id',
            'doctor_id',
            'patient_name',
            'stars',
            'comment',
            'created_at',
        )

    def get_patient_name(self, obj):
        return f'{obj.patient.first_name} {obj.patient.last_name}'.strip() or obj.patient.email


class CreateRatingSerializer(serializers.Serializer):
    """A patient rates one of their completed appointments, exactly once."""

    appointment = serializers.PrimaryKeyRelatedField(queryset=Appointment.objects.all())
    stars = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_appointment(self, appt):
        user = self.context['request'].user
        if appt.patient_id != user.id:
            raise serializers.ValidationError('You can only rate your own appointment.')
        if appt.status != Appointment.Status.COMPLETED:
            raise serializers.ValidationError('Only a completed visit can be rated.')
        if Rating.objects.filter(appointment=appt).exists():
            raise serializers.ValidationError('This appointment is already rated.')
        return appt
