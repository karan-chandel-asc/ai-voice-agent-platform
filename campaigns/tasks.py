from celery import shared_task


@shared_task(bind=True)
def run_campaign(self, campaign_id):
    """Outbound dialing removed — voice runtime now lives outside this Django app (e.g. Retell)."""
    from .models import Campaign

    campaign = Campaign.objects.get(id=campaign_id)
    campaign.status = "paused"
    campaign.save(update_fields=["status"])
    raise RuntimeError(
        "Twilio outbound campaigns were removed. Use your Retell agent for live calls."
    )
