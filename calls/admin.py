from django.contrib import admin
from .models import CallLog, CallTranscript


class CallTranscriptInline(admin.TabularInline):
    model = CallTranscript
    extra = 0
    readonly_fields = ["speaker", "text", "langgraph_node", "timestamp"]


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ["caller_phone", "agent", "direction", "status", "outcome", "duration_seconds", "created_at"]
    list_filter = ["direction", "status", "outcome", "was_transferred"]
    search_fields = ["caller_phone", "twilio_call_sid"]
    inlines = [CallTranscriptInline]
    readonly_fields = ["created_at"]
