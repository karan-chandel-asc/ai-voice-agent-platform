from django.contrib import admin
from .models import Agent, ElevenLabsVoice, Booking, UserTool, AgentUserTool


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ["agent_name", "owner", "phone_number", "status", "language", "created_at"]
    list_filter = ["status", "language"]
    search_fields = ["agent_name", "owner__email", "phone_number"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ElevenLabsVoice)
class ElevenLabsVoiceAdmin(admin.ModelAdmin):
    list_display = ["name", "voice_id", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "voice_id"]


@admin.register(UserTool)
class UserToolAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "tool_type", "is_active", "created_at"]
    list_filter = ["is_active", "tool_type"]
    search_fields = ["name", "owner__email"]


admin.site.register(Booking)
admin.site.register(AgentUserTool)
