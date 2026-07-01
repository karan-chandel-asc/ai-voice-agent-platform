from rest_framework import serializers
from .models import AgentDocument


class AgentDocumentSerializer(serializers.ModelSerializer):
    agent_name     = serializers.CharField(source='agent.agent_name', read_only=True)
    file_size      = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()

    class Meta:
        model = AgentDocument
        fields = [
            "id", "agent", "agent_name", "title", "file", "content",
            "status", "chunk_count", "file_size", "file_size_display",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "chunk_count", "created_at", "updated_at"]

    def validate_agent(self, agent):
        if agent.owner != self.context["request"].user:
            raise serializers.ValidationError("Agent not found.")
        return agent

    def get_file_size(self, obj):
        try:
            return obj.file.size if obj.file else 0
        except Exception:
            return 0

    def get_file_size_display(self, obj):
        try:
            size = obj.file.size if obj.file else 0
        except Exception:
            size = 0
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
