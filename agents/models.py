import uuid
from django.db import models
from django.conf import settings


class Agent(models.Model):
    STATUS_CHOICES = [
        ("live", "Live"),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner            = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agents"
    )
    agent_name       = models.CharField(max_length=100)
    elevenlabs_voice = models.ForeignKey(
        "ElevenLabsVoices",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents",
    )
    system_prompt    = models.TextField(blank=True)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default="live")
    language         = models.CharField(max_length=20, default="en-US")
    phone_number     = models.CharField(max_length=20, blank=True, default="")
    retell_agent_id  = models.CharField(max_length=100, blank=True, default="")
    retell_llm_id    = models.CharField(max_length=100, blank=True, default="")
    retell_voice_id  = models.CharField(max_length=255, blank=True, default="")
    retell_voice_name = models.CharField(max_length=100, blank=True, default="")
    retell_version   = models.IntegerField(null=True, blank=True)
    is_published     = models.BooleanField(default=False)
    channel          = models.CharField(max_length=40, blank=True, default="voice")
    tools_count      = models.PositiveIntegerField(default=0)
    tools_data       = models.JSONField(default=list, blank=True)
    retell_snapshot  = models.JSONField(default=dict, blank=True)
    last_synced_at   = models.DateTimeField(null=True, blank=True)
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
            models.Index(fields=["retell_agent_id"], name="agent_retell_id_idx"),
        ]

    def __str__(self):
        return self.agent_name


class ElevenLabsVoices(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=100)
    voice_id   = models.CharField(max_length=255, unique=True)
    recording_url = models.URLField(blank=True, null=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agents_elevenlabsvoice"  # keep existing table after rename
        ordering = ["name"]
        indexes = [
            models.Index(fields=["voice_id"], name="voice_voice_id_idx"),
            models.Index(fields=["is_active"], name="voice_active_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.voice_id})"


class RetellLanguage(models.Model):
    """Retell locale codes (from create-agent Language enum)."""

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code       = models.CharField(max_length=20, unique=True)
    label      = models.CharField(max_length=100)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["label"]
        indexes = [
            models.Index(fields=["code"], name="retell_lang_code_idx"),
            models.Index(fields=["is_active"], name="retell_lang_active_idx"),
        ]

    def __str__(self):
        return f"{self.label} ({self.code})"


class RetellPhoneNumber(models.Model):
    """Phone numbers synced from Retell (and optionally seeded from Twilio env)."""

    id                   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number         = models.CharField(max_length=20, unique=True)
    phone_number_pretty  = models.CharField(max_length=40, blank=True, default="")
    nickname             = models.CharField(max_length=100, blank=True, default="")
    phone_number_type    = models.CharField(max_length=40, blank=True, default="")
    assigned_agent       = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="retell_phones",
    )
    inbound_retell_agent_id = models.CharField(max_length=100, blank=True, default="")
    is_active            = models.BooleanField(default=True)
    last_synced_at       = models.DateTimeField(null=True, blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["phone_number"]
        indexes = [
            models.Index(fields=["phone_number"], name="retell_phone_num_idx"),
            models.Index(fields=["is_active"], name="retell_phone_active_idx"),
        ]

    def __str__(self):
        return self.phone_number_pretty or self.phone_number


class Booking(models.Model):
    BOOKING_TYPE_CHOICES = [
        ("room", "Room Booking"),
        ("table", "Table Booking"),
    ]
    ROOM_TYPE_CHOICES = [
        ("Deluxe Room", "Deluxe Room"),
        ("Superior Room", "Superior Room"),
        ("Family Room", "Family Room"),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent        = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings"
    )
    call_sid     = models.CharField(max_length=64, blank=True)
    booking_type = models.CharField(max_length=10, choices=BOOKING_TYPE_CHOICES, default="table")
    guest_name   = models.CharField(max_length=100)
    guest_email  = models.EmailField(blank=True)
    guest_phone  = models.CharField(max_length=30, blank=True, default="")
    guests       = models.PositiveSmallIntegerField(default=1)
    room_type    = models.CharField(max_length=40, blank=True, default="")
    special_requests = models.TextField(blank=True, default="")
    nights       = models.PositiveSmallIntegerField(null=True, blank=True)
    total_price  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
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


class GuestLead(models.Model):
    """Sales lead when a caller is interested but does not complete a reservation."""

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent           = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name="guest_leads"
    )
    call_sid        = models.CharField(max_length=64, blank=True, default="")
    guest_name      = models.CharField(max_length=100)
    phone_number    = models.CharField(max_length=30)
    email           = models.EmailField(blank=True, default="")
    check_in        = models.DateField(null=True, blank=True)
    check_out       = models.DateField(null=True, blank=True)
    number_of_guests = models.PositiveSmallIntegerField(null=True, blank=True)
    room_type       = models.CharField(max_length=40, blank=True, default="")
    notes           = models.TextField(blank=True, default="")
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agent"], name="guest_lead_agent_idx"),
            models.Index(fields=["created_at"], name="guest_lead_created_idx"),
        ]

    def __str__(self):
        return f"Lead: {self.guest_name} ({self.phone_number})"


class Escalation(models.Model):
    """Staff escalation when the AI receptionist cannot handle the call."""

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent        = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name="escalations"
    )
    call_sid     = models.CharField(max_length=64, blank=True, default="")
    caller_name  = models.CharField(max_length=100, blank=True, default="")
    phone_number = models.CharField(max_length=30, blank=True, default="")
    reason       = models.TextField()
    priority     = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")
    is_resolved  = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agent"], name="escalation_agent_idx"),
            models.Index(fields=["priority"], name="escalation_priority_idx"),
            models.Index(fields=["is_resolved"], name="escalation_resolved_idx"),
        ]

    def __str__(self):
        return f"[{self.priority}] {self.reason[:60]}"
