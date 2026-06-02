from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.permissions import IsAdmin, IsDoctor

from .models import DoctorAvailability, DoctorProfile, DocUpdateRequest
from .serializers import (
    DoctorAvailabilitySerializer,
    DoctorProfileSerializer,
    DoctorProfileWriteSerializer,
    DoctorPublicSerializer,
    DocUpdateRequestSerializer,
)


def approved_doctors():
    return (
        DoctorProfile.objects.select_related('user', 'specialty')
        .filter(user__role=User.Role.DOCTOR, user__status=User.Status.APPROVED)
        .order_by('user__first_name', 'pk')  # stable order so pagination is consistent
    )


class ApprovedDoctorListView(generics.ListAPIView):
    """GET /api/v1/doctors/ - browse approved doctors.

    Public so a guest can run their landing-page searches before signing in; the
    front-end limits guests to a couple of searches and gates *viewing a doctor's
    details / booking* behind login. The detail endpoint below stays auth-only.

    ?search=<name> matches first/last name, ?specialty=<id> filters by specialty.
    """

    permission_classes = [AllowAny]
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


class BestDoctorsView(generics.ListAPIView):
    """GET /api/v1/doctors/best/ - top rated doctors for the guest landing page.

    public on purpose (the landing shows them before login), capped to 6.
    """

    serializer_class = DoctorPublicSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return (
            approved_doctors()
            .annotate(avg=Avg('ratings_received__stars'), n=Count('ratings_received'))
            .order_by('-avg', '-n')[:6]
        )


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


class MyUpdateRequestView(generics.ListCreateAPIView):
    """GET/POST /api/v1/doctors/me/update-requests/ - file resume/license changes."""

    serializer_class = DocUpdateRequestSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return DocUpdateRequest.objects.filter(doctor_id=self.request.user.pk)

    def perform_create(self, serializer):
        prof, _ = DoctorProfile.objects.get_or_create(user=self.request.user)
        u = self.request.user
        name = f'{u.first_name} {u.last_name}'.strip() or u.email
        serializer.save(doctor=prof, doctor_name=name)


class AdminUpdateRequestListView(generics.ListAPIView):
    """GET /api/v1/doctors/update-requests/ - admin queue (?status=pending)."""

    serializer_class = DocUpdateRequestSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = DocUpdateRequest.objects.select_related('doctor__user')
        st = self.request.query_params.get('status')
        return qs.filter(status=st) if st else qs


class ApproveUpdateRequestView(APIView):
    """POST .../update-requests/<id>/approve/ - patch the new docs onto the profile."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        req = get_object_or_404(DocUpdateRequest, pk=pk)
        prof = req.doctor
        if req.resume_url:
            prof.resume_url = req.resume_url
        if req.license_url:
            prof.license_url = req.license_url
        prof.save(update_fields=['resume_url', 'license_url', 'updated_at'])
        req.status = DocUpdateRequest.Status.APPROVED
        req.save(update_fields=['status'])
        return Response(DocUpdateRequestSerializer(req).data)


class RejectUpdateRequestView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        req = get_object_or_404(DocUpdateRequest, pk=pk)
        req.status = DocUpdateRequest.Status.REJECTED
        req.save(update_fields=['status'])
        return Response(DocUpdateRequestSerializer(req).data)
