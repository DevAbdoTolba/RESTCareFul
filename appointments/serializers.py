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
            'display_status',
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
            'my_rating',
        )

    my_rating = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()

    def get_display_status(self, obj):
        # `paid` is a standalone flag, so a still-unpaid pending booking reads as
        # 'unpaid' (waiting for payment) and only becomes 'pending' (waiting for
        # the doctor to confirm) once it's paid. Every other status is itself.
        if obj.status == Appointment.Status.PENDING and not obj.paid:
            return 'unpaid'
        return obj.status

    def _full_name(self, user):
        return f'{user.first_name} {user.last_name}'.strip() or user.email

    def get_doctor_name(self, obj):
        return self._full_name(obj.doctor.user)

    def get_patient_name(self, obj):
        return self._full_name(obj.patient)

    def get_my_rating(self, obj):
        # The (single) rating left for this appointment, embedded so the history
        # UI doesn't need a second request to know if it's already rated.
        from ratings.models import Rating

        rating = Rating.objects.filter(appointment=obj).first()
        return {'stars': rating.stars, 'comment': rating.comment} if rating else None


class BookAppointmentSerializer(serializers.Serializer):
    """Patient books a specific 30-min time inside one of the doctor's open windows."""

    doctor = serializers.IntegerField()
    date = serializers.DateField()
    time = serializers.TimeField()
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        from accounts.models import User
        from doctors.models import DoctorProfile

        prof = DoctorProfile.objects.filter(
            pk=attrs['doctor'],
            user__role=User.Role.DOCTOR,
            user__status=User.Status.APPROVED,
        ).first()
        if prof is None:
            raise serializers.ValidationError({'doctor': 'No such approved doctor.'})

        now = timezone.now()
        if attrs['date'] < now.date() or (
            attrs['date'] == now.date() and attrs['time'] <= now.time()
        ):
            raise serializers.ValidationError('Cannot book a slot in the past.')

        window = DoctorAvailability.objects.filter(
            doctor=prof,
            date=attrs['date'],
            is_available=True,
            start_time__lte=attrs['time'],
            end_time__gt=attrs['time'],
        ).first()
        if window is None:
            raise serializers.ValidationError('That time is not open for booking.')

        attrs['doctor_profile'] = prof
        return attrs
