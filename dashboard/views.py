from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from appointments.models import Appointment
from core.permissions import IsAdmin


class DashboardMetricsView(APIView):
    """GET /api/v1/dashboard/metrics/ - admin-only overview counts.

    wip: revenue + paid totals coming next.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(
            {
                'users': User.objects.count(),
                'doctors': User.objects.filter(role=User.Role.DOCTOR).count(),
                'patients': User.objects.filter(role=User.Role.PATIENT).count(),
                'pending_doctors': User.objects.filter(
                    role=User.Role.DOCTOR, status=User.Status.PENDING
                ).count(),
                'appointments': Appointment.objects.count(),
            }
        )
