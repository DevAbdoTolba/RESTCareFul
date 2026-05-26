from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'date', 'time', 'status', 'paid')
    list_filter = ('status', 'paid', 'date')
    search_fields = ('patient__email', 'doctor__user__email')
    raw_id_fields = ('patient', 'doctor')
