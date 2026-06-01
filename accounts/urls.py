"""
Auth + user endpoints. Mounted at /api/v1/auth/ from config.urls.

SimpleJWT's TokenObtainPairView accepts whatever USERNAME_FIELD is on the user
model — since ours is `email`, login takes {"email": ..., "password": ...}.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    AdminUserDetailView,
    AdminUserListView,
    ApproveDoctorView,
    ChangePasswordView,
    MeView,
    RegisterView,
    RejectDoctorView,
    UpdateProfileView,
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('me/profile/', UpdateProfileView.as_view(), name='profile-update'),
    path('me/password/', ChangePasswordView.as_view(), name='change-password'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/doctors/<int:pk>/approve/', ApproveDoctorView.as_view(), name='approve-doctor'),
    path('admin/doctors/<int:pk>/reject/', RejectDoctorView.as_view(), name='reject-doctor'),
]
