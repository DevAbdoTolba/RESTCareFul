from rest_framework import serializers

from appointments.models import Appointment

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    doctor_id = serializers.IntegerField(read_only=True)
    patient_id = serializers.IntegerField(read_only=True)
    appointment_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Payment
        fields = (
            'id',
            'appointment_id',
            'patient_id',
            'doctor_id',
            'amount',
            'status',
            'paypal_order_id',
            'paypal_capture_id',
            'created_at',
        )


class CreatePaymentSerializer(serializers.Serializer):
    appointment = serializers.PrimaryKeyRelatedField(queryset=Appointment.objects.all())
