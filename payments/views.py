from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.permissions import IsAdmin, IsPatient

from . import paypal
from .models import Payment
from .serializers import CreatePaymentSerializer, PaymentSerializer


def _mark_paid(payment, capture_id=None):
    payment.status = Payment.Status.PAID
    if capture_id:
        payment.paypal_capture_id = capture_id
    payment.save(update_fields=['status', 'paypal_capture_id', 'updated_at'])
    appt = payment.appointment
    appt.paid = True
    appt.amount_paid = payment.amount
    appt.save(update_fields=['paid', 'amount_paid', 'updated_at'])


class CreatePaymentView(APIView):
    """POST /api/v1/payments/create/ {appointment, return_url?, cancel_url?}.

    Opens a real PayPal order and returns its `approval_url` for the buyer to be
    redirected to. When credentials aren't configured it returns a DEMO order
    (approval_url=null) so the flow still works offline.
    """

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
        try:
            order = paypal.create_order(
                amount,
                reference=f'appointment-{appt.id}',
                return_url=request.data.get('return_url'),
                cancel_url=request.data.get('cancel_url'),
            )
        except paypal.PayPalError as exc:
            return Response(
                {'detail': 'Could not start PayPal payment.', 'paypal': exc.body},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payment = Payment.objects.create(
            appointment=appt,
            patient=request.user,
            doctor=appt.doctor,
            amount=amount,
            paypal_order_id=order['id'],
        )
        return Response(
            {
                **PaymentSerializer(payment).data,
                'approval_url': order['approval_url'],
                'demo': order['demo'],
            },
            status=status.HTTP_201_CREATED,
        )


class CapturePaymentView(APIView):
    """POST /api/v1/payments/<id>/capture/ -> capture the approved order, mark paid."""

    permission_classes = [IsPatient]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, patient=request.user)
        if payment.status == Payment.Status.PAID:
            return Response(PaymentSerializer(payment).data)

        try:
            result = paypal.capture_order(payment.paypal_order_id)
        except paypal.PayPalError as exc:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=['status', 'updated_at'])
            return Response(
                {'detail': 'Capture failed.', 'paypal': exc.body},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if result['status'] != 'COMPLETED':
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=['status', 'updated_at'])
            return Response(
                {'detail': f'Payment not completed (PayPal: {result["status"]}).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _mark_paid(payment, result.get('capture_id'))
        return Response(PaymentSerializer(payment).data)


class VerifyPaymentView(APIView):
    """POST /api/v1/payments/<id>/verify/ -> re-sync a payment whose capture was interrupted."""

    permission_classes = [IsPatient]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, patient=request.user)
        if payment.status == Payment.Status.PAID:
            return Response(PaymentSerializer(payment).data)

        try:
            order = paypal.get_order(payment.paypal_order_id)
        except paypal.PayPalError as exc:
            return Response(
                {'detail': 'Could not verify with PayPal.', 'paypal': exc.body},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        paypal_status = order.get('status')
        if paypal_status == 'COMPLETED':
            _mark_paid(payment)
            return Response(PaymentSerializer(payment).data)
        if paypal_status == 'APPROVED':
            # buyer approved but our capture never landed — capture now
            result = paypal.capture_order(payment.paypal_order_id)
            if result['status'] == 'COMPLETED':
                _mark_paid(payment, result.get('capture_id'))
                return Response(PaymentSerializer(payment).data)

        return Response(
            {'detail': f'PayPal order is {paypal_status}. Approve it, then try again.'},
            status=status.HTTP_400_BAD_REQUEST,
        )


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
