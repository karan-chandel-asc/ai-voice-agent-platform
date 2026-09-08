from rest_framework import serializers
from .models import CallLog, CallTranscript


class CallTranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallTranscript
        fields = ["id", "speaker", "text", "timestamp"]


class CallLogSerializer(serializers.ModelSerializer):
    agent_name = serializers.SerializerMethodField()
    sentiment = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()

    class Meta:
        model = CallLog
        fields = [
            "id", "agent", "agent_name", "twilio_call_sid",
            "caller_phone", "direction", "status",
            "reason", "duration_seconds", "duration", "sentiment_score",
            "sentiment", "was_transferred", "started_at", "ended_at", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_agent_name(self, obj):
        return obj.agent.agent_name if obj.agent_id else "—"

    def get_sentiment(self, obj):
        val = (obj.sentiment_score or "").strip().lower()
        if not val:
            return None
        if val in ("positive", "negative", "neutral"):
            return val
        # Legacy float strings from before CharField migration
        try:
            num = float(val)
            if num > 0.05:
                return "positive"
            if num < -0.05:
                return "negative"
            return "neutral"
        except (TypeError, ValueError):
            return None

    def get_duration(self, obj):
        minutes, seconds = divmod(obj.duration_seconds or 0, 60)
        return f"{minutes}:{seconds:02d}"


class CallLogDetailSerializer(CallLogSerializer):
    transcripts = CallTranscriptSerializer(many=True, read_only=True)

    class Meta(CallLogSerializer.Meta):
        fields = CallLogSerializer.Meta.fields + ["transcripts"]
