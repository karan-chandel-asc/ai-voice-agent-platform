from django.contrib import admin
from .models import Agent, ElevenLabsVoice, PhoneNumber, Booking, UserTool


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display    = ["agent_name", "owner", "status", "language", "created_at"]
    list_filter     = ["status", "language"]
    search_fields   = ["agent_name", "owner__email"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ElevenLabsVoice)
class ElevenLabsVoiceAdmin(admin.ModelAdmin):
    list_display  = ["name", "voice_id", "is_active", "created_at"]
    list_filter   = ["is_active"]
    search_fields = ["name", "voice_id"]


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display  = ["phone_number", "agent", "status", "assigned_at", "created_at"]
    list_filter   = ["status"]
    search_fields = ["phone_number", "agent__agent_name"]
    readonly_fields = ["created_at", "updated_at"]

admin.site.register(Booking)
admin.site.register(UserTool)