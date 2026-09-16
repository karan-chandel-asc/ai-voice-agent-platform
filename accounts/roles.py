"""Deskline role helpers: admin CRUD vs viewer read-only."""
from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission

User = get_user_model()

# Production portfolio admin — viewers always mirror this workspace.
DESKLINE_ADMIN_EMAIL = "deskline@demo.io"


def is_deskline_admin(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return getattr(user, "is_deskline_admin", True)


def workspace_owner(user):
    """User whose agents/calls/bookings should be visible.

    Admins see their own workspace.
    Viewers always see deskline@demo.io's workspace (same agents/calls/etc).
    """
    if is_deskline_admin(user):
        return user

    admin = (
        User.objects.filter(
            email__iexact=DESKLINE_ADMIN_EMAIL,
            is_active=True,
        )
        .order_by("created_at")
        .first()
    )
    if admin:
        return admin

    # Fallback: any active admin
    return (
        User.objects.filter(role=User.ROLE_ADMIN, is_active=True)
        .order_by("created_at")
        .first()
        or user
    )


class IsDesklineAdmin(BasePermission):
    """Allow safe methods for any auth user; mutating methods require admin."""

    message = "Read-only account. Only an admin can create, update, or delete."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return is_deskline_admin(request.user)


class IsDesklineAdminStrict(BasePermission):
    """Require admin for every method (use on write-only endpoints)."""

    message = "Read-only account. Only an admin can perform this action."

    def has_permission(self, request, view):
        return is_deskline_admin(request.user)
