"""
URL routes for the specialties slice. Mounted at /api/v1/specialties/.

Owner: see .github/CODEOWNERS. Add endpoints here only.
"""

from django.urls import path

from .views import (
    SpecialtyDetailView,
    SpecialtyListView,
    SuggestionApproveView,
    SuggestionListCreateView,
    SuggestionRejectView,
)

app_name = 'specialties'

urlpatterns = [
    path('', SpecialtyListView.as_view(), name='list'),
    path('suggestions/', SuggestionListCreateView.as_view(), name='suggestions'),
    path('suggestions/<int:pk>/approve/', SuggestionApproveView.as_view(), name='suggestion-approve'),
    path('suggestions/<int:pk>/reject/', SuggestionRejectView.as_view(), name='suggestion-reject'),
    path('<int:pk>/', SpecialtyDetailView.as_view(), name='detail'),
]
