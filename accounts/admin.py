from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin tweaked for email-as-username + the new role/status fields."""

    list_display = ('email', 'role', 'status', 'is_staff', 'is_superuser', 'created_at')
    list_filter = ('role', 'status', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            'Personal',
            {
                'fields': (
                    'first_name',
                    'last_name',
                    'phone_number',
                    'gender',
                    'date_of_birth',
                    'description',
                )
            },
        ),
        ('Role & approval', {'fields': ('role', 'status')}),
        (
            'Permissions',
            {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')},
        ),
        ('Timestamps', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'password1', 'password2', 'role', 'status'),
            },
        ),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'date_joined')
