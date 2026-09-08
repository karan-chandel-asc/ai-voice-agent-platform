from rest_framework import serializers
from .models import Agent, ElevenLabsVoices, RetellLanguage, RetellPhoneNumber


class ElevenLabsVoicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElevenLabsVoices
        fields = ["id", "name", "voice_id", "recording_url"]


class RetellLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetellLanguage
        fields = ["id", "code", "label"]


class RetellPhoneNumberSerializer(serializers.ModelSerializer):
    assigned_agent_name = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = RetellPhoneNumber
        fields = [
            "id", "phone_number", "phone_number_pretty", "nickname",
            "phone_number_type", "assigned_agent", "assigned_agent_name",
            "is_available", "inbound_retell_agent_id",
        ]

    def get_assigned_agent_name(self, obj):
        return obj.assigned_agent.agent_name if obj.assigned_agent_id else None

    def get_is_available(self, obj):
        return obj.assigned_agent_id is None


class AgentListSerializer(serializers.ModelSerializer):
    owner_email  = serializers.EmailField(source="owner.email", read_only=True)
    voice_name   = serializers.SerializerMethodField()
    total_calls  = serializers.IntegerField(read_only=True, default=0)
    avg_duration_seconds = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Agent
        fields = [
            "id", "owner_email", "agent_name", "voice_name", "system_prompt",
            "status", "language", "phone_number", "retell_agent_id",
            "retell_voice_id", "retell_voice_name", "tools_count", "tools_data",
            "is_published", "channel", "last_synced_at",
            "total_calls", "avg_duration_seconds",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_voice_name(self, obj):
        if obj.elevenlabs_voice:
            return obj.elevenlabs_voice.name
        return obj.retell_voice_name or None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Safe defaults when queryset was not annotated
        if data.get("total_calls") is None:
            data["total_calls"] = getattr(instance, "total_calls", None)
            if data["total_calls"] is None:
                data["total_calls"] = instance.calls.count() if hasattr(instance, "calls") else 0
        if data.get("avg_duration_seconds") is None:
            data["avg_duration_seconds"] = int(getattr(instance, "avg_duration_seconds", 0) or 0)
        else:
            data["avg_duration_seconds"] = int(data["avg_duration_seconds"] or 0)
        return data


class AgentDetailSerializer(serializers.ModelSerializer):
    owner_email            = serializers.EmailField(source="owner.email", read_only=True)
    voice_name             = serializers.SerializerMethodField()
    voice_id               = serializers.SerializerMethodField()
    elevenlabs_voice_db_id = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            "id", "owner_email", "agent_name", "voice_name", "voice_id",
            "elevenlabs_voice_db_id", "system_prompt", "status", "language",
            "phone_number", "retell_agent_id", "retell_llm_id",
            "retell_voice_id", "retell_voice_name", "retell_version",
            "is_published", "channel", "tools_count", "tools_data",
            "retell_snapshot", "last_synced_at",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_voice_name(self, obj):
        if obj.elevenlabs_voice:
            return obj.elevenlabs_voice.name
        return obj.retell_voice_name or None

    def get_voice_id(self, obj):
        if obj.elevenlabs_voice:
            return obj.elevenlabs_voice.voice_id
        return obj.retell_voice_id or None

    def get_elevenlabs_voice_db_id(self, obj):
        return str(obj.elevenlabs_voice.id) if obj.elevenlabs_voice else None
