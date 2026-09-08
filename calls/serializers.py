from rest_framework import serializers
from .models import CallLog, CallTranscript


class CallTranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallTranscript
        fields = ["id", "speaker", "text", "timestamp"]


class CallLogSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.agent_name", read_only=True)
    outcome_label = serializers.CharField(source="get_outcome_display", read_only=True)
    sentiment = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()

    class Meta:
        model = CallLog
        fields = [
            "id", "agent", "agent_name", "twilio_call_sid",
            "caller_phone", "direction", "status", "outcome", "outcome_label",
            "reason", "duration_seconds", "duration", "sentiment_score",
            "sentiment", "was_transferred", "started_at", "ended_at", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_sentiment(self, obj):
        if obj.sentiment_score is None:
            return "neutral"
        if obj.sentiment_score > 0.05:
            return "positive"
        if obj.sentiment_score < -0.05:
            return "negative"
        return "neutral"

    def get_duration(self, obj):
        minutes, seconds = divmod(obj.duration_seconds or 0, 60)
        return f"{minutes}:{seconds:02d}"


class CallLogDetailSerializer(CallLogSerializer):
    transcripts = CallTranscriptSerializer(many=True, read_only=True)

    class Meta(CallLogSerializer.Meta):
        fields = CallLogSerializer.Meta.fields + ["transcripts"]
