from django.contrib import admin

from .models import Rating


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'doctor', 'patient', 'stars', 'created_at')
    list_filter = ('stars',)
    search_fields = ('doctor__user__email', 'patient__email', 'comment')
    raw_id_fields = ('appointment', 'doctor', 'patient')
