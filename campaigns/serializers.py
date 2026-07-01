from rest_framework import serializers
from .models import Campaign, CampaignNumber


class CampaignNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignNumber
        fields = ["id", "phone_number", "contact_name", "status", "attempted_at"]


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = [
            "id", "agent", "name", "description", "numbers_csv",
            "scheduled_at", "status", "total_calls", "answered",
            "confirmed", "failed", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "total_calls", "answered", "confirmed", "failed", "created_at", "updated_at"]

    def validate_agent(self, agent):
        if agent.owner != self.context["request"].user:
            raise serializers.ValidationError("Agent not found.")
        return agent
