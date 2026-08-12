import uuid
from django.db import models
from django.conf import settings


class Agent(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("live", "Live"),
        ("paused", "Paused"),
        ("error", "Error"),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner            = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agents"
    )
    agent_name       = models.CharField(max_length=100)
    elevenlabs_voice = models.ForeignKey(
        "ElevenLabsVoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents",
    )
    system_prompt    = models.TextField(blank=True)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    language         = models.CharField(max_length=10, default="en")
    phone_number     = models.CharField(max_length=20, blank=True, default="")
    is_demo          = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner"], name="agent_owner_idx"),
            models.Index(fields=["status"], name="agent_status_idx"),
            models.Index(fields=["created_at"], name="agent_created_idx"),
            models.Index(fields=["phone_number"], name="agent_phone_idx"),
        ]

    def __str__(self):
        return self.agent_name


class ElevenLabsVoice(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=100)
    voice_id   = models.CharField(max_length=255, unique=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["voice_id"], name="voice_voice_id_idx"),
            models.Index(fields=["is_active"], name="voice_active_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.voice_id})"


class UserTool(models.Model):
    """Single-user tool library. Attach to agents via AgentUserTool."""

    TOOL_TYPE_CHOICES = [
        ("builtin", "Built-in"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_tools"
    )
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    tool_type   = models.CharField(max_length=20, choices=TOOL_TYPE_CHOICES, default="builtin")
    parameters  = models.JSONField(default=dict, blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner"], name="usertool_owner_idx"),
            models.Index(fields=["is_active"], name="usertool_active_idx"),
        ]

    def __str__(self):
        return self.name


class AgentUserTool(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent      = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="user_tools")
    user_tool  = models.ForeignKey(UserTool, on_delete=models.CASCADE, related_name="agent_links")
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["agent", "user_tool"]]
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["agent"], name="agentusertool_agent_idx"),
        ]

    def __str__(self):
        return f"{self.agent.agent_name} → {self.user_tool.name}"


class Booking(models.Model):
    BOOKING_TYPE_CHOICES = [
        ("room", "Room Booking"),
        ("table", "Table Booking"),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent        = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings"
    )
    call_sid     = models.CharField(max_length=64, blank=True)
    booking_type = models.CharField(max_length=10, choices=BOOKING_TYPE_CHOICES, default="table")
    guest_name   = models.CharField(max_length=100)
    guest_email  = models.EmailField(blank=True)
    guests       = models.PositiveSmallIntegerField(default=1)
    reservation_date_time = models.DateTimeField(null=True, blank=True)
    check_in     = models.DateField(null=True, blank=True)
    check_out    = models.DateField(null=True, blank=True)
    is_confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agent"], name="booking_agent_idx"),
            models.Index(fields=["check_in"], name="booking_checkin_idx"),
            models.Index(fields=["call_sid"], name="booking_callsid_idx"),
            models.Index(fields=["booking_type"], name="booking_type_idx"),
        ]

    def __str__(self):
        when = self.check_in.isoformat() if self.check_in else "no-date"
        return f"[{self.booking_type}] {self.guest_name} — {when}"
