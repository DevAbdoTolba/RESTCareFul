from django.db.models import Avg
from rest_framework import serializers

from .models import DoctorAvailability, DoctorProfile, DocUpdateRequest


class DoctorPublicSerializer(serializers.ModelSerializer):
    """what a patient sees on a doctor card / detail page. no resume+license."""

    id = serializers.IntegerField(source='pk', read_only=True)
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    specialty_id = serializers.IntegerField(read_only=True)
    specialty = serializers.CharField(source='specialty.name', read_only=True, default=None)
    description = serializers.CharField(source='user.description', read_only=True)
    rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = (
            'id',
            'name',
            'email',
            'specialty_id',
            'specialty',
            'hourly_rate',
            'description',
            'rating',
            'rating_count',
        )

    def get_name(self, obj):
        full = f'{obj.user.first_name} {obj.user.last_name}'.strip()
        return full or obj.user.email

    def get_rating(self, obj):
        avg = obj.ratings_received.aggregate(a=Avg('stars'))['a']
        return round(avg, 2) if avg is not None else None

    def get_rating_count(self, obj):
        return obj.ratings_received.count()


class DoctorProfileSerializer(DoctorPublicSerializer):
    """owner/admin view - adds the private resume + license."""

    class Meta(DoctorPublicSerializer.Meta):
        fields = DoctorPublicSerializer.Meta.fields + (
            'resume_url',
            'license_url',
            'created_at',
            'updated_at',
        )


class DoctorProfileWriteSerializer(serializers.ModelSerializer):
    """what a doctor may set on their own profile (specialty + price + docs)."""

    class Meta:
        model = DoctorProfile
        fields = ('specialty', 'hourly_rate', 'resume_url', 'license_url')

    def validate_specialty(self, value):
        # A doctor must always have a specialty — it can be changed, never cleared.
        if value is None:
            raise serializers.ValidationError('A doctor must have a specialty.')
        return value


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    """an open window the doctor declares. is_available flips when booked."""

    class Meta:
        model = DoctorAvailability
        fields = ('id', 'date', 'start_time', 'end_time', 'is_available')
        read_only_fields = ('is_available',)

    def validate(self, attrs):
        if attrs['end_time'] <= attrs['start_time']:
            raise serializers.ValidationError('end_time must be after start_time.')
        return attrs


class DocUpdateRequestSerializer(serializers.ModelSerializer):
    """doctor files a resume/license change, admin approves it onto the profile."""

    # doctor pk == the user id, so the admin UI can map a request to a user row.
    doctor_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = DocUpdateRequest
        fields = (
            'id',
            'doctor_id',
            'doctor_name',
            'resume_url',
            'license_url',
            'status',
            'created_at',
        )
        read_only_fields = ('doctor_id', 'doctor_name', 'status', 'created_at')
