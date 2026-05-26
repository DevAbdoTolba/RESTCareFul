"""
Auth + user endpoints. Mounted at /api/v1/auth/ from config.urls.

SimpleJWT's TokenObtainPairView accepts whatever USERNAME_FIELD is on the user
model — since ours is `email`, login takes {"email": ..., "password": ...}.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import MeView, RegisterView

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('me/', MeView.as_view(), name='me'),
]
