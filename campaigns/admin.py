from django.contrib import admin
from .models import Campaign, CampaignNumber


class CampaignNumberInline(admin.TabularInline):
    model = CampaignNumber
    extra = 0


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ["name", "agent", "status", "total_calls", "answered", "confirmed", "scheduled_at"]
    list_filter = ["status"]
    inlines = [CampaignNumberInline]
