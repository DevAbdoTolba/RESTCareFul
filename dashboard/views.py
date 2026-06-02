from decimal import Decimal

from django.db.models import Avg, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from appointments.models import Appointment
from core.permissions import IsAdmin
from payments.models import Payment
from ratings.models import Rating

# platform keeps 12% of every paid booking.
PLATFORM_CUT = Decimal('0.12')


class DashboardMetricsView(APIView):
    """GET /api/v1/dashboard/metrics/ - admin-only overview."""

    permission_classes = [IsAdmin]

    def get(self, request):
        # Run the time-based transitions first: expire overdue-unconfirmed
        # bookings (refunds drop from the totals) and complete due ones.
        from appointments.services import sweep_appointments

        sweep_appointments()

        total_paid = Payment.objects.filter(status=Payment.Status.PAID).aggregate(s=Sum('amount'))[
            's'
        ] or Decimal('0')
        avg_rating = Rating.objects.aggregate(a=Avg('stars'))['a']

        return Response(
            {
                'users': User.objects.count(),
                'doctors': User.objects.filter(role=User.Role.DOCTOR).count(),
                'patients': User.objects.filter(role=User.Role.PATIENT).count(),
                'pending_doctors': User.objects.filter(
                    role=User.Role.DOCTOR, status=User.Status.PENDING
                ).count(),
                'appointments': Appointment.objects.count(),
                'completed_appointments': Appointment.objects.filter(
                    status=Appointment.Status.COMPLETED
                ).count(),
                'total_paid': total_paid,
                'platform_revenue': round(total_paid * PLATFORM_CUT, 2),
                'total_ratings': Rating.objects.count(),
                'average_rating': round(avg_rating, 2) if avg_rating is not None else None,
            }
        )
