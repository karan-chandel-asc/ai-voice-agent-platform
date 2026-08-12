from rest_framework import serializers
from calls.models import CallLog
from agents.models import Booking


class BookingSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.agent_name", read_only=True, default="")
    nights     = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id", "booking_type", "agent_name",
            "guest_name", "guest_email", "guests",
            "check_in", "check_out", "nights",
            "is_confirmed", "confirmed_at", "created_at",
        ]

    def get_nights(self, obj):
        if obj.check_in and obj.check_out:
            return (obj.check_out - obj.check_in).days
        return None


class BookingDetailSerializer(serializers.ModelSerializer):
    nights = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id", "booking_type", "guest_name", "guest_email", "guests",
            "check_in", "check_out", "nights",
            "is_confirmed", "confirmed_at",
        ]

    def get_nights(self, obj):
        if obj.check_in and obj.check_out:
            return (obj.check_out - obj.check_in).days
        return None


class BookingCallSerializer(serializers.ModelSerializer):
    agent_name   = serializers.CharField(source="agent.agent_name", read_only=True)
    duration     = serializers.SerializerMethodField()
    booking      = serializers.SerializerMethodField()
    booking_type = serializers.SerializerMethodField()

    class Meta:
        model = CallLog
        fields = [
            "id", "twilio_call_sid", "caller_phone", "agent_name",
            "duration_seconds", "duration", "sentiment_score",
            "status", "created_at", "started_at", "ended_at",
            "booking", "booking_type",
        ]

    def get_duration(self, obj):
        minutes, seconds = divmod(obj.duration_seconds or 0, 60)
        return f"{minutes}:{seconds:02d}"

    def get_booking(self, obj):
        booking_map = self.context.get("booking_map", {})
        b = booking_map.get(obj.twilio_call_sid)
        return BookingDetailSerializer(b).data if b else None

    def get_booking_type(self, obj):
        booking_map = self.context.get("booking_map", {})
        b = booking_map.get(obj.twilio_call_sid)
        return b.booking_type if b else None


class DashboardStatsSerializer(serializers.Serializer):
    total_agents         = serializers.IntegerField()
    live_agents          = serializers.IntegerField()
    total_calls          = serializers.IntegerField()
    room_bookings        = serializers.IntegerField()
    table_bookings       = serializers.IntegerField()
    avg_duration_seconds = serializers.FloatField()


class BookingStatsSerializer(serializers.Serializer):
    total_booking = serializers.IntegerField()
    rooms_booking = serializers.IntegerField()
    tables        = serializers.IntegerField()
    this_month    = serializers.IntegerField()
    avg_duration  = serializers.IntegerField()
    avg_sentiment = serializers.FloatField()
