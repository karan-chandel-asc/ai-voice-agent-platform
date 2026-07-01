import uuid
from django.db import models


class Campaign(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("paused", "Paused"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE, related_name="campaigns"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    numbers_csv = models.FileField(upload_to="campaigns/csv/")
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total_calls = models.IntegerField(default=0)
    answered = models.IntegerField(default=0)
    confirmed = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.status})"


class CampaignNumber(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("dialing", "Dialing"),
        ("answered", "Answered"),
        ("no-answer", "No Answer"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="numbers")
    phone_number = models.CharField(max_length=20)
    contact_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    call = models.ForeignKey(
        "calls.CallLog", on_delete=models.SET_NULL, null=True, blank=True
    )
    attempted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.phone_number} ({self.status})"
