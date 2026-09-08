from django.contrib import admin
from .models import (
    Agent, ElevenLabsVoices, Booking, GuestLead, Escalation,
    RetellLanguage, RetellPhoneNumber,
)


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = [
        "agent_name", "owner", "phone_number", "status", "language",
        "tools_count", "retell_agent_id", "is_published", "created_at",
    ]
    list_filter = ["status", "language", "is_published"]
    search_fields = ["agent_name", "owner__email", "phone_number", "retell_agent_id"]
    readonly_fields = ["created_at", "updated_at", "last_synced_at", "retell_snapshot"]


@admin.register(ElevenLabsVoices)
class ElevenLabsVoicesAdmin(admin.ModelAdmin):
    list_display = ["name", "voice_id", "recording_url", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "voice_id", "recording_url"]


@admin.register(RetellLanguage)
class RetellLanguageAdmin(admin.ModelAdmin):
    list_display = ["label", "code", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["label", "code"]


@admin.register(RetellPhoneNumber)
class RetellPhoneNumberAdmin(admin.ModelAdmin):
    list_display = [
        "phone_number", "nickname", "phone_number_type",
        "assigned_agent", "is_active", "last_synced_at",
    ]
    list_filter = ["is_active", "phone_number_type"]
    search_fields = ["phone_number", "nickname"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "guest_name", "booking_type", "room_type", "check_in", "check_out",
        "guests", "total_price", "is_confirmed", "created_at",
    ]
    list_filter = ["booking_type", "room_type", "is_confirmed"]
    search_fields = ["guest_name", "guest_email", "guest_phone", "call_sid"]


@admin.register(GuestLead)
class GuestLeadAdmin(admin.ModelAdmin):
    list_display = ["guest_name", "phone_number", "room_type", "check_in", "created_at"]
    search_fields = ["guest_name", "phone_number", "email"]


@admin.register(Escalation)
class EscalationAdmin(admin.ModelAdmin):
    list_display = ["priority", "caller_name", "phone_number", "is_resolved", "created_at"]
    list_filter = ["priority", "is_resolved"]
    search_fields = ["caller_name", "phone_number", "reason"]
