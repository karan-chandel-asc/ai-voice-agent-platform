import uuid
from django.db import models


class CallLog(models.Model):
    DIRECTION_CHOICES = [
        ("inbound", "Inbound"),
        ("web_call", "Web Call"),
    ]
    STATUS_CHOICES = [
        ("in-progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("no-answer", "No Answer"),
        ("transferred", "Transferred"),
    ]
    SENTIMENT_CHOICES = [
        ("positive", "Positive"),
        ("negative", "Negative"),
        ("neutral", "Neutral"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.SET_NULL, null=True, blank=True, related_name="calls"
    )
    twilio_call_sid = models.CharField(max_length=64, unique=True)
    # Filled on call_ended; call_started may only store call_id
    caller_phone = models.CharField(max_length=20, blank=True, default="")
    direction = models.CharField(
        max_length=10, choices=DIRECTION_CHOICES, blank=True, default="web_call"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in-progress")
    reason = models.CharField(max_length=100, blank=True)
    duration_seconds = models.IntegerField(default=0)
    sentiment_score = models.CharField(
        max_length=20, choices=SENTIMENT_CHOICES, blank=True, default=""
    )
    was_transferred = models.BooleanField(default=False)
    recording_url = models.URLField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.direction or 'call'} {self.twilio_call_sid} — {self.status}"


class CallTranscript(models.Model):
    SPEAKER_CHOICES = [("agent", "Agent"), ("caller", "Caller")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(CallLog, on_delete=models.CASCADE, related_name="transcripts")
    speaker = models.CharField(max_length=10, choices=SPEAKER_CHOICES)
    text = models.TextField()
    langgraph_node = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.speaker}] {self.text[:60]}"
