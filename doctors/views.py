from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.permissions import IsDoctor

from .models import DoctorAvailability, DoctorProfile
from .serializers import (
    DoctorAvailabilitySerializer,
    DoctorProfileSerializer,
    DoctorProfileWriteSerializer,
    DoctorPublicSerializer,
)


def approved_doctors():
    return (
        DoctorProfile.objects.select_related('user', 'specialty')
        .filter(user__role=User.Role.DOCTOR, user__status=User.Status.APPROVED)
    )


class ApprovedDoctorListView(generics.ListAPIView):
    """GET /api/v1/doctors/ - browse approved doctors.

    ?search=<name> matches first/last name, ?specialty=<id> filters by specialty.
    """

    serializer_class = DoctorPublicSerializer

    def get_queryset(self):
        qs = approved_doctors()
        specialty = self.request.query_params.get('specialty')
        if specialty:
            qs = qs.filter(specialty_id=specialty)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(user__first_name__icontains=search) | qs.filter(
                user__last_name__icontains=search
            )
        return qs


class ApprovedDoctorDetailView(generics.RetrieveAPIView):
    """GET /api/v1/doctors/<id>/ - one doctor (login required to view)."""

    serializer_class = DoctorPublicSerializer
    queryset = approved_doctors()


class MyDoctorProfileView(APIView):
    """GET/PUT /api/v1/doctors/me/ - a doctor manages their own profile.

    PUT upserts so a freshly registered doctor can fill it in right after signup.
    """

    permission_classes = [IsDoctor]

    def get(self, request):
        prof = (
            DoctorProfile.objects.select_related('user', 'specialty')
            .filter(pk=request.user.pk)
            .first()
        )
        if prof is None:
            return Response({'detail': 'No doctor profile yet.'}, status=404)
        return Response(DoctorProfileSerializer(prof).data)

    def put(self, request):
        prof, _ = DoctorProfile.objects.get_or_create(user=request.user)
        ser = DoctorProfileWriteSerializer(prof, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        prof.refresh_from_db()
        return Response(DoctorProfileSerializer(prof).data)


class MyAvailabilityView(generics.ListCreateAPIView):
    """GET/POST /api/v1/doctors/me/availability/ - the doctor's own windows."""

    serializer_class = DoctorAvailabilitySerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return DoctorAvailability.objects.filter(doctor_id=self.request.user.pk)

    def perform_create(self, serializer):
        prof, _ = DoctorProfile.objects.get_or_create(user=self.request.user)
        serializer.save(doctor=prof)


class MyAvailabilityDeleteView(generics.DestroyAPIView):
    """DELETE /api/v1/doctors/me/availability/<id>/ - drop a window."""

    permission_classes = [IsDoctor]

    def get_queryset(self):
        return DoctorAvailability.objects.filter(doctor_id=self.request.user.pk)


class DoctorOpenSlotsView(generics.ListAPIView):
    """GET /api/v1/doctors/<id>/availability/ - bookable future slots only.

    Past or already-taken windows are never returned, so a patient can't try to
    book an outdated slot.
    """

    serializer_class = DoctorAvailabilitySerializer

    def get_queryset(self):
        return DoctorAvailability.objects.filter(
            doctor_id=self.kwargs['pk'],
            is_available=True,
            date__gte=timezone.now().date(),
        )
