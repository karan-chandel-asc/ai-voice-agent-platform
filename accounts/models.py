import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Single-operator account for the hotel/restaurant desk."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    business_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    plan = models.CharField(
        max_length=20,
        choices=[("free", "Free"), ("pro", "Pro"), ("enterprise", "Enterprise")],
        default="free",
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
        return self.email
