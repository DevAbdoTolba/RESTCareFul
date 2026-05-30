from rest_framework import serializers

from .models import Specialty, SpecialtySuggestion


class SpecialtySerializer(serializers.ModelSerializer):
    doctor_count = serializers.SerializerMethodField()

    class Meta:
        model = Specialty
        fields = ('id', 'name', 'description', 'doctor_count')

    def get_doctor_count(self, obj):
        # how many approved doctors carry this specialty (used on the landing).
        return obj.doctors.filter(user__status='approved').count()


class SpecialtySuggestionSerializer(serializers.ModelSerializer):
    proposed_by = serializers.EmailField(source='proposed_by.email', read_only=True)

    class Meta:
        model = SpecialtySuggestion
        fields = ('id', 'name', 'status', 'proposed_by', 'created_at')
        read_only_fields = ('status', 'proposed_by', 'created_at')
