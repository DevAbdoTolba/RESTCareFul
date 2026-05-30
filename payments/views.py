from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsPatient

from .models import Payment
from .paypal import new_capture_id, new_order_id
from .serializers import CreatePaymentSerializer, PaymentSerializer


class CreatePaymentView(APIView):
    """POST /api/v1/payments/create/ {appointment} -> opens a pending paypal order."""

    permission_classes = [IsPatient]

    def post(self, request):
        ser = CreatePaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        appt = ser.validated_data['appointment']

        if appt.patient_id != request.user.id:
            return Response({'detail': 'Not your appointment.'}, status=status.HTTP_403_FORBIDDEN)
        if appt.paid:
            return Response({'detail': 'Already paid.'}, status=status.HTTP_400_BAD_REQUEST)

        amount = appt.doctor.hourly_rate or 0
        payment = Payment.objects.create(
            appointment=appt,
            patient=request.user,
            doctor=appt.doctor,
            amount=amount,
            paypal_order_id=new_order_id(),
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class CapturePaymentView(APIView):
    """POST /api/v1/payments/<id>/capture/ -> mark paid + flag the appointment."""

    permission_classes = [IsPatient]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, patient=request.user)
        if payment.status == Payment.Status.PAID:
            return Response(PaymentSerializer(payment).data)

        payment.status = Payment.Status.PAID
        payment.paypal_capture_id = new_capture_id()
        payment.save(update_fields=['status', 'paypal_capture_id', 'updated_at'])

        appt = payment.appointment
        appt.paid = True
        appt.amount_paid = payment.amount
        appt.save(update_fields=['paid', 'amount_paid', 'updated_at'])

        return Response(PaymentSerializer(payment).data)
