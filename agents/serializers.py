from rest_framework import serializers
from .models import Agent, AgentUserTool, ElevenLabsVoice, PhoneNumber, UserTool


# ── Catalog / lookup serializers ───────────────────────────────────────────────

class PhoneNumberSerializer(serializers.ModelSerializer):
    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model  = PhoneNumber
        fields = ["id", "phone_number", "status", "assigned_to", "assigned_at", "created_at"]

    def get_assigned_to(self, obj):
        return obj.agent.agent_name if obj.agent else None


class ElevenLabsVoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ElevenLabsVoice
        fields = ["id", "name", "voice_id"]


# ── Agent nested serializers ───────────────────────────────────────────────────

class AgentUserToolMiniSerializer(serializers.ModelSerializer):
    user_tool_id  = serializers.UUIDField(source="user_tool.id",          read_only=True)
    name          = serializers.CharField(source="user_tool.name",        read_only=True)
    description   = serializers.CharField(source="user_tool.description", read_only=True)
    tool_type     = serializers.CharField(source="user_tool.tool_type",   read_only=True)
    webhook_url   = serializers.URLField(source="user_tool.webhook_url",  read_only=True)
    parameters    = serializers.JSONField(source="user_tool.parameters",  read_only=True)

    class Meta:
        model  = AgentUserTool
        fields = ["id", "user_tool_id", "name", "description", "tool_type", "webhook_url", "parameters", "is_active"]


# ── Agent serializers ──────────────────────────────────────────────────────────

class AgentListSerializer(serializers.ModelSerializer):
    owner_email  = serializers.EmailField(source="owner.email", read_only=True)
    phone_number = serializers.SerializerMethodField()
    user_tools   = AgentUserToolMiniSerializer(many=True, read_only=True)
    voice_name   = serializers.SerializerMethodField()

    class Meta:
        model  = Agent
        fields = [
            "id", "owner_email", "agent_name", "voice_name", "system_prompt",
            "status", "language", "phone_number", "user_tools", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_phone_number(self, obj):
        number = obj.assigned_number
        return number.phone_number if number else None

    def get_voice_name(self, obj):
        return obj.elevenlabs_voice.name if obj.elevenlabs_voice else None


class AgentDetailSerializer(serializers.ModelSerializer):
    owner_email            = serializers.EmailField(source="owner.email", read_only=True)
    phone_number           = serializers.SerializerMethodField()
    phone_number_db_id     = serializers.SerializerMethodField()
    user_tools             = AgentUserToolMiniSerializer(many=True, read_only=True)
    voice_name             = serializers.SerializerMethodField()
    voice_id               = serializers.SerializerMethodField()
    elevenlabs_voice_db_id = serializers.SerializerMethodField()

    class Meta:
        model  = Agent
        fields = [
            "id", "owner_email", "agent_name", "voice_name", "voice_id",
            "elevenlabs_voice_db_id", "system_prompt", "status", "language",
            "phone_number", "phone_number_db_id", "user_tools", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_phone_number(self, obj):
        number = obj.assigned_number
        return number.phone_number if number else None

    def get_phone_number_db_id(self, obj):
        number = obj.assigned_number
        return str(number.id) if number else None

    def get_voice_name(self, obj):
        return obj.elevenlabs_voice.name if obj.elevenlabs_voice else None

    def get_voice_id(self, obj):
        return obj.elevenlabs_voice.voice_id if obj.elevenlabs_voice else None

    def get_elevenlabs_voice_db_id(self, obj):
        return str(obj.elevenlabs_voice.id) if obj.elevenlabs_voice else None


# ── UserTool serializers ───────────────────────────────────────────────────────

class UserToolSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)

    class Meta:
        model  = UserTool
        fields = [
            "id", "owner_email", "name", "description", "tool_type",
            "webhook_url", "parameters", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "owner_email", "created_at", "updated_at"]
