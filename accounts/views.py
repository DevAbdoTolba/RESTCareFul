from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdmin

from .models import User
from .serializers import (
    ChangePasswordSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)


def _display_name(user):
    return f'{user.first_name} {user.last_name}'.strip() or user.email


class RegisterView(generics.CreateAPIView):
    """POST /api/v1/auth/register/ — open signup for patients and doctors."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        from core.emails import notify_account_created

        notify_account_created(user.email, _display_name(user))


class MeView(generics.RetrieveAPIView):
    """GET /api/v1/auth/me/ — the current user. The React app calls this on bootstrap."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UpdateProfileView(generics.UpdateAPIView):
    """PATCH /api/v1/auth/me/profile/ — edit your own profile fields."""

    serializer_class = ProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch', 'put']

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """POST /api/v1/auth/me/password/ — change password (old one required)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        user = request.user
        user.set_password(ser.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response({'detail': 'Password updated.'})


class AdminUserListView(generics.ListAPIView):
    """GET /api/v1/auth/admin/users/ — admin browses users (?role= , ?status=).

    The admin dashboard hits this with ?role=doctor&status=pending to render the
    approval queue.
    """

    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = User.objects.all()
        role = self.request.query_params.get('role')
        status_ = self.request.query_params.get('status')
        if role:
            qs = qs.filter(role=role)
        if status_:
            qs = qs.filter(status=status_)
        return qs


class AdminUserDetailView(APIView):
    """GET /api/v1/auth/admin/users/<id>/ — full user incl. doctor docs.

    The approve dialog needs a pending doctor's resume/license (which live on the
    DoctorProfile, not the User), so they're merged in here.
    """

    permission_classes = [IsAdmin]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = UserSerializer(user).data
        if user.role == User.Role.DOCTOR:
            from django.db.models import Avg, Count, Sum

            from appointments.models import Appointment
            from doctors.models import DoctorProfile
            from payments.models import Payment
            from ratings.models import Rating

            prof = DoctorProfile.objects.select_related('specialty').filter(pk=user.pk).first()
            if prof:
                data.update(
                    {
                        'specialty_id': prof.specialty_id,
                        'specialty': prof.specialty.name if prof.specialty else None,
                        'hourly_rate': prof.hourly_rate,
                        'resume_url': prof.resume_url,
                        'license_url': prof.license_url,
                    }
                )
            # Stats the admin needs to judge a doctor at a glance.
            appts = Appointment.objects.filter(doctor_id=user.pk)
            rating = Rating.objects.filter(doctor_id=user.pk).aggregate(
                avg=Avg('stars'), count=Count('appointment')
            )
            earned = (
                Payment.objects.filter(doctor_id=user.pk, status=Payment.Status.PAID).aggregate(
                    s=Sum('amount')
                )['s']
                or 0
            )
            data['rating'] = {
                'average': round(rating['avg'], 2) if rating['avg'] is not None else None,
                'count': rating['count'],
            }
            data['stats'] = {
                'appointments': appts.count(),
                'completed': appts.filter(status=Appointment.Status.COMPLETED).count(),
                'total_earned': earned,
            }
        return Response(data)


class ApproveDoctorView(APIView):
    """POST /api/v1/auth/admin/doctors/<id>/approve/ — let the doctor be booked."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        doctor = get_object_or_404(User, pk=pk, role=User.Role.DOCTOR)
        doctor.status = User.Status.APPROVED
        doctor.save(update_fields=['status', 'updated_at'])
        self._approve_proposed_specialty(doctor)
        return Response(UserSerializer(doctor).data)

    def _approve_proposed_specialty(self, doctor):
        """A doctor who proposed a new specialty at signup has no specialty yet.

        Approving the account also approves that pending suggestion: it becomes a
        real Specialty and gets linked onto the doctor's profile, so no approved
        doctor is ever left without a specialty.
        """
        from doctors.models import DoctorProfile
        from specialties.models import Specialty, SpecialtySuggestion

        suggestion = (
            SpecialtySuggestion.objects.filter(
                proposed_by=doctor, status=SpecialtySuggestion.Status.PENDING
            )
            .order_by('-created_at')
            .first()
        )
        if suggestion is None:
            return
        suggestion.status = SpecialtySuggestion.Status.APPROVED
        suggestion.save(update_fields=['status'])
        specialty, _ = Specialty.objects.get_or_create(name=suggestion.name)
        profile = DoctorProfile.objects.filter(pk=doctor.pk).first()
        if profile is not None and profile.specialty_id is None:
            profile.specialty = specialty
            profile.save(update_fields=['specialty', 'updated_at'])
        from core.emails import notify_specialty_decision

        notify_specialty_decision(doctor.email, _display_name(doctor), specialty.name, approved=True)


class RejectDoctorView(APIView):
    """POST /api/v1/auth/admin/doctors/<id>/reject/ — deny a pending doctor."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        doctor = get_object_or_404(User, pk=pk, role=User.Role.DOCTOR)
        doctor.status = User.Status.REJECTED
        doctor.save(update_fields=['status', 'updated_at'])
        return Response(UserSerializer(doctor).data)


class BanUserView(APIView):
    """POST /api/v1/auth/admin/users/<id>/ban/ — revoke access for any non-admin.

    Flips is_active off too, so a banned account can't obtain a JWT at all.
    """

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target.role == User.Role.ADMIN:
            return Response(
                {'detail': 'Admins cannot be banned.'}, status=status.HTTP_400_BAD_REQUEST
            )
        target.status = User.Status.BANNED
        target.is_active = False
        target.save(update_fields=['status', 'is_active', 'updated_at'])
        from core.emails import notify_account_banned

        notify_account_banned(target.email, _display_name(target))
        return Response(UserSerializer(target).data)


class UnbanUserView(APIView):
    """POST /api/v1/auth/admin/users/<id>/unban/ — restore a banned account."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        target.status = User.Status.APPROVED
        target.is_active = True
        target.save(update_fields=['status', 'is_active', 'updated_at'])
        from core.emails import notify_account_unbanned

        notify_account_unbanned(target.email, _display_name(target))
        return Response(UserSerializer(target).data)
