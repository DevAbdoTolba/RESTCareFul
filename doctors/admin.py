from django.contrib import admin

from .models import DoctorAvailability, DoctorProfile


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty', 'hourly_rate', 'created_at')
    list_filter = ('specialty',)
    search_fields = ('user__email',)
    raw_id_fields = ('user',)


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'date', 'start_time', 'end_time', 'is_available')
    list_filter = ('is_available', 'date')
    raw_id_fields = ('doctor',)
