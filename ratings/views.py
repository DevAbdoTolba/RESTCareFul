from django.db.models import Avg, Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsPatient

from .models import Rating
from .serializers import CreateRatingSerializer, RatingSerializer


class CreateRatingView(APIView):
    """POST /api/v1/ratings/ {appointment, stars, comment} — rate a completed visit."""

    permission_classes = [IsPatient]

    def post(self, request):
        ser = CreateRatingSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        appt = ser.validated_data['appointment']
        rating = Rating.objects.create(
            appointment=appt,
            patient=request.user,
            doctor=appt.doctor,
            stars=ser.validated_data['stars'],
            comment=ser.validated_data['comment'],
        )
        return Response(RatingSerializer(rating).data, status=status.HTTP_201_CREATED)


class DoctorRatingsView(APIView):
    """GET /api/v1/ratings/doctor/<id>/ — a doctor's ratings + average summary."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        qs = Rating.objects.filter(doctor_id=pk).select_related('patient')
        agg = qs.aggregate(avg=Avg('stars'), count=Count('appointment'))
        return Response(
            {
                'doctor_id': pk,
                'average': round(agg['avg'], 2) if agg['avg'] is not None else None,
                'count': agg['count'],
                'ratings': RatingSerializer(qs, many=True).data,
            }
        )
