from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.permissions import IsDoctor

from .models import DoctorProfile
from .serializers import (
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
