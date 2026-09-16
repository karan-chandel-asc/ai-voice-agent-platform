import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Single-operator account for the hotel/restaurant desk.

    Email is the login username field.
    Stores business profile details.
    role=admin can CRUD; role=viewer can visit/read only.
    """

    ROLE_ADMIN = "admin"
    ROLE_VIEWER = "viewer"
    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admin"),
        (ROLE_VIEWER, "Viewer"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    business_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    plan = models.CharField(max_length=20, blank=True, default="")
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_ADMIN,
        help_text="admin = full CRUD; viewer = read-only console access",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        """Return email as the admin display label."""
        return self.email

    @property
    def is_deskline_admin(self):
        return (self.role or self.ROLE_ADMIN) == self.ROLE_ADMIN
