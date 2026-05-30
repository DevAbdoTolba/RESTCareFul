from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.permissions import IsAdmin, IsDoctor

from .models import Specialty, SpecialtySuggestion
from .serializers import SpecialtySerializer, SpecialtySuggestionSerializer


class SpecialtyListView(generics.ListAPIView):
    """GET /api/v1/specialties/ - open list, the guest landing page reads this."""

    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    permission_classes = [AllowAny]
    pagination_class = None


class SpecialtyDetailView(generics.RetrieveAPIView):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    permission_classes = [AllowAny]


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
        return Response(SpecialtySerializer(specialty).data)


class SuggestionRejectView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        suggestion = get_object_or_404(SpecialtySuggestion, pk=pk)
        suggestion.status = SpecialtySuggestion.Status.REJECTED
        suggestion.save(update_fields=['status'])
        return Response(SpecialtySuggestionSerializer(suggestion).data)
