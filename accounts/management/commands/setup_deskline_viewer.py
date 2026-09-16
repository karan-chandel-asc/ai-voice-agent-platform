"""
Set up Deskline production demo roles:

  Admin  (full CRUD):  deskline@demo.io / desklinedemo
  Viewer (read-only):  viewer@deskline.io / viewerdemo

Viewer can open the console and see ALL agents / calls / bookings / KB
owned by deskline@demo.io, but cannot create, update, or delete anything.

Usage (local or production):
  python manage.py setup_deskline_viewer
"""
from django.core.management.base import BaseCommand

from accounts.models import CustomUser
from accounts.roles import DESKLINE_ADMIN_EMAIL


ADMIN_EMAIL = DESKLINE_ADMIN_EMAIL
ADMIN_PASSWORD = "desklinedemo"
VIEWER_EMAIL = "viewer@deskline.io"
VIEWER_PASSWORD = "viewerdemo"


class Command(BaseCommand):
    help = (
        "Ensure deskline@demo.io is admin and create a read-only viewer "
        "that mirrors that account's agents/calls (no CRUD)."
    )

    def handle(self, *args, **options):
        # --- Admin: production portfolio account ---
        admin, created = CustomUser.objects.get_or_create(
            email=ADMIN_EMAIL,
            defaults={
                "username": "deskline_admin",
                "first_name": "Deskline",
                "last_name": "Admin",
                "business_name": "The Harbor Inn & Bistro",
                "phone": "+14155550100",
                "role": CustomUser.ROLE_ADMIN,
                "is_active": True,
            },
        )
        admin.role = CustomUser.ROLE_ADMIN
        admin.is_active = True
        if not (admin.business_name or "").strip():
            admin.business_name = "The Harbor Inn & Bistro"
        admin.set_password(ADMIN_PASSWORD)
        admin.save()
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'} ADMIN  "
            f"{ADMIN_EMAIL} / {ADMIN_PASSWORD}  (full CRUD)"
        ))

        # --- Viewer: same business, read-only mirror of admin workspace ---
        viewer, created = CustomUser.objects.get_or_create(
            email=VIEWER_EMAIL,
            defaults={
                "username": "deskline_viewer",
                "first_name": "Deskline",
                "last_name": "Viewer",
                "business_name": admin.business_name or "The Harbor Inn & Bistro",
                "phone": "+14155550101",
                "role": CustomUser.ROLE_VIEWER,
                "is_active": True,
            },
        )
        viewer.role = CustomUser.ROLE_VIEWER
        viewer.business_name = admin.business_name or viewer.business_name
        viewer.is_active = True
        viewer.set_password(VIEWER_PASSWORD)
        viewer.save()
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'} VIEWER {VIEWER_EMAIL} / {VIEWER_PASSWORD}  (read-only)"
        ))
        self.stdout.write(
            f"Viewer mirrors workspace of {ADMIN_EMAIL} "
            "(agents, calls, bookings, knowledge) — no create/update/delete."
        )
