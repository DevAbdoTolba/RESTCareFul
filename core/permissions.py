"""
Shared DRF permissions — owned by `core` and imported by every domain app's
views. Centralising these means "what is an approved doctor?" has exactly one
answer in the codebase.
"""

from rest_framework import permissions

from accounts.models import User


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == User.Role.ADMIN)


class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == User.Role.DOCTOR)


class IsApprovedDoctor(permissions.BasePermission):
    """A doctor that an admin has approved — gates visibility from patients."""

    def has_permission(self, request, view):
        u = request.user
        return bool(
            u
            and u.is_authenticated
            and u.role == User.Role.DOCTOR
            and u.status == User.Status.APPROVED
        )


class IsPatient(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == User.Role.PATIENT)


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level guard. Looks at common owner attributes (`patient`, `user`,
    `proposed_by`) — extend in the view if your model uses a different name.
    """

    def has_object_permission(self, request, view, obj):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if u.role == User.Role.ADMIN:
            return True
        owner = (
            getattr(obj, 'patient', None)
            or getattr(obj, 'user', None)
            or getattr(obj, 'proposed_by', None)
        )
        return owner == u
