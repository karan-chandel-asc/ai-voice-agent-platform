from rest_framework import serializers
from .models import GoogleCalendarCredential, Integration

class GoogleCalendarCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleCalendarCredential
        fields = ["id", "calendar_id", "token_expiry", "created_at"]
        read_only_fields = ["id", "created_at"]


class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Integration
        fields = ["id", "type", "is_connected", "webhook_url", "connected_at", "updated_at"]
        read_only_fields = ["id", "connected_at", "updated_at"]
