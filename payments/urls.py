"""
URL routes for the payments slice. Mounted at /api/v1/payments/.

Owner: see .github/CODEOWNERS. Add endpoints here only.
"""

from django.urls import path

from .views import (
    CapturePaymentView,
    CreatePaymentView,
    MyPaymentsView,
    RefundPaymentView,
)

app_name = 'payments'

urlpatterns = [
    path('', MyPaymentsView.as_view(), name='mine'),
    path('create/', CreatePaymentView.as_view(), name='create'),
    path('<int:pk>/capture/', CapturePaymentView.as_view(), name='capture'),
    path('<int:pk>/refund/', RefundPaymentView.as_view(), name='refund'),
]
