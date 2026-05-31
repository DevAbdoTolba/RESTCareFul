from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
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


class RegisterView(generics.CreateAPIView):
    """POST /api/v1/auth/register/ — open signup for patients and doctors."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


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


class ApproveDoctorView(APIView):
    """POST /api/v1/auth/admin/doctors/<id>/approve/ — let the doctor be booked."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        doctor = get_object_or_404(User, pk=pk, role=User.Role.DOCTOR)
        doctor.status = User.Status.APPROVED
        doctor.save(update_fields=['status', 'updated_at'])
        return Response(UserSerializer(doctor).data)


class RejectDoctorView(APIView):
    """POST /api/v1/auth/admin/doctors/<id>/reject/ — deny a pending doctor."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        doctor = get_object_or_404(User, pk=pk, role=User.Role.DOCTOR)
        doctor.status = User.Status.REJECTED
        doctor.save(update_fields=['status', 'updated_at'])
        return Response(UserSerializer(doctor).data)
