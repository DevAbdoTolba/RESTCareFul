from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.permissions import IsAdmin, IsDoctor

from .models import Specialty, SpecialtySuggestion
from .serializers import SpecialtySerializer, SpecialtySuggestionSerializer


class SpecialtyListView(generics.ListCreateAPIView):
    """GET (public, landing page) + POST (admin creates a specialty)."""

    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    pagination_class = None

    def get_permissions(self):
        return [IsAdmin()] if self.request.method == 'POST' else [AllowAny()]


class SpecialtyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET (public) + PATCH/DELETE (admin) for one specialty."""

    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer

    def get_permissions(self):
        return [AllowAny()] if self.request.method == 'GET' else [IsAdmin()]


class SuggestionListCreateView(generics.ListCreateAPIView):
    """Doctors propose a missing specialty. Admin sees all, a doctor sees own."""

    serializer_class = SpecialtySuggestionSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsDoctor()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = SpecialtySuggestion.objects.select_related('proposed_by')
        if self.request.user.role != User.Role.ADMIN:
            qs = qs.filter(proposed_by=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(proposed_by=self.request.user)


class SuggestionApproveView(APIView):
    """POST .../suggestions/<id>/approve/ - admin turns a suggestion into a real Specialty."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        suggestion = get_object_or_404(SpecialtySuggestion, pk=pk)
        suggestion.status = SpecialtySuggestion.Status.APPROVED
        suggestion.save(update_fields=['status'])
        specialty, _ = Specialty.objects.get_or_create(name=suggestion.name)
        _notify_suggestion(suggestion, approved=True)
        return Response(SpecialtySerializer(specialty).data)


class SuggestionRejectView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        suggestion = get_object_or_404(SpecialtySuggestion, pk=pk)
        suggestion.status = SpecialtySuggestion.Status.REJECTED
        suggestion.save(update_fields=['status'])
        _notify_suggestion(suggestion, approved=False)
        return Response(SpecialtySuggestionSerializer(suggestion).data)


def _notify_suggestion(suggestion, *, approved):
    """Email the proposing doctor that their specialty was approved/rejected."""
    doctor = suggestion.proposed_by
    if not doctor:
        return
    from core.emails import notify_specialty_decision

    name = f'{doctor.first_name} {doctor.last_name}'.strip() or doctor.email
    notify_specialty_decision(doctor.email, name, suggestion.name, approved=approved)
