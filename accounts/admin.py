from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ["email", "username", "business_name", "plan", "is_staff"]
    list_filter = ["plan", "is_staff", "is_active"]
    search_fields = ["email", "username", "business_name"]
    ordering = ["-created_at"]
    fieldsets = UserAdmin.fieldsets + (
        ("Profile", {"fields": ("business_name", "phone", "plan")}),
    )
