from django.contrib import admin

from .models import Specialty, SpecialtySuggestion


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(SpecialtySuggestion)
class SpecialtySuggestionAdmin(admin.ModelAdmin):
    list_display = ('name', 'proposed_by', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'proposed_by__email')
