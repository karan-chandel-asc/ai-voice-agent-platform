from django.contrib import admin
from .models import AgentDocument, DocumentChunk


@admin.register(AgentDocument)
class AgentDocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "agent", "status", "chunk_count", "created_at"]
    list_filter = ["status"]
