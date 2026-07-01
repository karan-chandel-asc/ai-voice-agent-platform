from celery import shared_task
from django.conf import settings


@shared_task(bind=True)
def run_campaign(self, campaign_id):
    from .models import Campaign, CampaignNumber
    campaign = Campaign.objects.get(id=campaign_id)
    campaign.status = "running"
    campaign.save(update_fields=["status"])

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        for number_obj in campaign.numbers.filter(status="pending"):
            number_obj.status = "dialing"
            number_obj.save(update_fields=["status"])
            client.calls.create(
                to=number_obj.phone_number,
                from_=campaign.agent.twilio_phone_number,
                url=f"{settings.FASTAPI_BASE_URL}/voice/outbound",
                status_callback=f"{settings.FASTAPI_BASE_URL}/voice/status",
            )

        campaign.status = "completed"
        campaign.save(update_fields=["status"])
    except Exception as exc:
        campaign.status = "paused"
        campaign.save(update_fields=["status"])
        raise self.retry(exc=exc, countdown=60, max_retries=3)
