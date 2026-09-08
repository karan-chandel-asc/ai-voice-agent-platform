from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin UI for CustomUser accounts.

    Extends Django UserAdmin with business fields.
    Supports search by email, username, and business.
    """

    list_display = ["email", "username", "business_name", "is_staff"]
    list_filter = ["is_staff", "is_active"]
    search_fields = ["email", "username", "business_name"]
    ordering = ["-created_at"]
    fieldsets = UserAdmin.fieldsets + (
        ("Profile", {"fields": ("business_name", "phone")}),
    )
