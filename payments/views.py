from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.permissions import IsAdmin, IsPatient

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


class MyPaymentsView(generics.ListAPIView):
    """GET /api/v1/payments/ - patient sees own, doctor sees received, admin all."""

    serializer_class = PaymentSerializer

    def get_queryset(self):
        u = self.request.user
        qs = Payment.objects.all()
        if u.role == User.Role.PATIENT:
            return qs.filter(patient=u)
        if u.role == User.Role.DOCTOR:
            return qs.filter(doctor_id=u.pk)
        return qs


class RefundPaymentView(APIView):
    """POST /api/v1/payments/<id>/refund/ - admin marks a payment refunded."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        payment.status = Payment.Status.REFUNDED
        payment.save(update_fields=['status', 'updated_at'])
        appt = payment.appointment
        appt.paid = False
        appt.amount_paid = 0
        appt.save(update_fields=['paid', 'amount_paid', 'updated_at'])
        return Response(PaymentSerializer(payment).data)
