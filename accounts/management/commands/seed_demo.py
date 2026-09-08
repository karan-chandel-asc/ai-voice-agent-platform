"""
Populate realistic hospitality demo data for portfolio screenshots.

Usage:
  python manage.py seed_demo
  python manage.py seed_demo --flush   # wipe this demo user's data first

Login after seeding:
  email:    demo@deskline.io
  password: demo1234
"""
from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta, time as dtime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import CustomUser
from agents.models import Agent, Booking, ElevenLabsVoices
from calls.models import CallLog, CallTranscript


DEMO_EMAIL = "demo@deskline.io"
DEMO_PASSWORD = "demo1234"

GUEST_NAMES = [
    ("Priya Sharma", "priya.sharma@email.com"),
    ("James Mitchell", "j.mitchell@email.com"),
    ("Aisha Khan", "aisha.k@email.com"),
    ("Carlos Rivera", "carlos.r@email.com"),
    ("Emily Chen", "emily.chen@email.com"),
    ("Omar Hassan", "omar.hassan@email.com"),
    ("Sofia Alvarez", "sofia.a@email.com"),
    ("Noah Patel", "noah.patel@email.com"),
    ("Grace Kim", "grace.kim@email.com"),
    ("Liam O'Brien", "liam.obrien@email.com"),
    ("Maya Singh", "maya.singh@email.com"),
    ("Daniel Park", "daniel.park@email.com"),
    ("Fatima Noor", "fatima.noor@email.com"),
    ("Ryan Cooper", "ryan.cooper@email.com"),
    ("Hana Suzuki", "hana.suzuki@email.com"),
    ("Marcus Webb", "marcus.webb@email.com"),
    ("Elena Rossi", "elena.rossi@email.com"),
    ("Arjun Mehta", "arjun.mehta@email.com"),
    ("Chloe Bennett", "chloe.b@email.com"),
    ("Yusuf Ali", "yusuf.ali@email.com"),
]

PHONES = [
    "+14155550101", "+14155550122", "+12125550334", "+13105550445",
    "+16175550556", "+17185550667", "+18085550778", "+19085550889",
    "+12025550990", "+13055551001", "+14085551112", "+15035551223",
]

INTENTS = [
    "room_booking", "table_reservation", "guest_faq", "room_service",
    "check_in_help", "spa_inquiry", "late_checkout", "menu_question",
]

TRANSCRIPTS = [
    ("agent", "Hello! Thank you for calling The Harbor Inn. This is Maya. May I have your name please?"),
    ("caller", "Hi, this is Priya Sharma. I'd like to book a room for two nights."),
    ("agent", "Of course, Priya. What dates would you like for check-in and check-out?"),
    ("caller", "Checking in tomorrow, checking out the day after."),
    ("agent", "Perfect. A room for two guests, two nights. Shall I confirm that booking for you?"),
    ("caller", "Yes, please confirm it."),
    ("agent", "You're all set. I've confirmed your room booking. Is there anything else I can help with?"),
    ("caller", "That's all, thank you!"),
]


class Command(BaseCommand):
    """Seed hospitality demo data for screenshots.

    Creates a demo user, agents, calls, and bookings.
    Use --flush to wipe existing demo data first.
    """

    help = "Seed hospitality demo data for screenshots (login: demo@deskline.io / demo1234)"

    def add_arguments(self, parser):
        """Register optional --flush flag for reseeding."""
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing demo user data before reseeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        """Create or refresh the full demo dataset."""
        if options["flush"]:
            deleted, _ = CustomUser.objects.filter(email=DEMO_EMAIL).delete()
            self.stdout.write(self.style.WARNING(f"Flushed demo user (+cascade): {deleted} objects"))

        user = self._user()
        voices = self._voices()
        agents = self._agents(user, voices)
        calls = self._calls(agents)
        self._transcripts(calls)
        bookings = self._bookings(agents, calls)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo data ready for screenshots."))
        self.stdout.write(f"  User:     {DEMO_EMAIL}")
        self.stdout.write(f"  Password: {DEMO_PASSWORD}")
        self.stdout.write(f"  Agents:   {len(agents)}")
        self.stdout.write(f"  Calls:    {len(calls)}")
        self.stdout.write(f"  Bookings: {bookings}")
        self.stdout.write("")
        self.stdout.write("Login, then open Dashboard / Agents / Bookings / Calls / Analytics.")

    def _user(self) -> CustomUser:
        """Create or update the demo operator account."""
        user, created = CustomUser.objects.get_or_create(

            email=DEMO_EMAIL,
            defaults={
                "username": "deskline_demo",
                "first_name": "Ava",
                "last_name": "Moreau",
                "business_name": "The Harbor Inn & Bistro",
                "phone": "+14155550100",
                "is_active": True,
            },
        )
        user.set_password(DEMO_PASSWORD)
        user.first_name = "Ava"
        user.last_name = "Moreau"
        user.business_name = "The Harbor Inn & Bistro"
        user.phone = "+14155550100"
        user.save()
        self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} demo user"))
        return user

    def _voices(self) -> list[ElevenLabsVoices]:
        """Ensure demo ElevenLabs voice rows exist."""
        specs = [

            ("Maya — Warm Concierge", "demo_voice_maya"),
            ("Alex — Restaurant Host", "demo_voice_alex"),
            ("Sofia — Soft Front Desk", "demo_voice_sofia"),
        ]
        voices = []
        for name, vid in specs:
            v, _ = ElevenLabsVoices.objects.get_or_create(
                voice_id=vid,
                defaults={"name": name, "is_active": True},
            )
            voices.append(v)
        return voices

    def _agents(self, user, voices) -> list[Agent]:
        """Create demo agents."""
        specs = [

            {
                "agent_name": "Front Desk Maya",
                "status": "live",
                "phone_number": "+18605551001",
                "is_demo": True,
                "voice": voices[0],
                "prompt": (
                    "You are Maya, the overnight front-desk voice agent for The Harbor Inn. "
                    "Help guests with room bookings, FAQs, and late-night requests. "
                    "Ask whether they need a room, a restaurant table, or both. "
                    "Confirm details before booking."
                ),
            },
            {
                "agent_name": "Bistro Host Alex",
                "status": "live",
                "phone_number": "+18605551002",
                "is_demo": False,
                "voice": voices[1],
                "prompt": (
                    "You are Alex, the restaurant host for Harbor Bistro. "
                    "Take table reservations, answer menu questions, and note dietary needs. "
                    "Confirm party size and date before booking."
                ),
            },
            {
                "agent_name": "Concierge Sofia",
                "status": "live",
                "phone_number": "+18605551003",
                "is_demo": False,
                "voice": voices[2],
                "prompt": "You are Sofia, a concierge agent for spa bookings and guest services.",
            },
            {
                "agent_name": "Events Bot",
                "status": "live",
                "phone_number": "+18605551004",
                "is_demo": False,
                "voice": voices[0] if voices else None,
                "prompt": "You handle private dining and events inquiries for the hotel.",
            },
        ]

        # Clear old demo agents for this user so reseed stays clean
        Agent.objects.filter(owner=user).exclude(
            agent_name__in=[s["agent_name"] for s in specs]
        ).delete()

        agents = []
        for spec in specs:
            agent, _ = Agent.objects.update_or_create(
                owner=user,
                agent_name=spec["agent_name"],
                defaults={
                    "status": spec["status"],
                    "phone_number": spec["phone_number"],
                    "is_demo": spec["is_demo"],
                    "elevenlabs_voice": spec["voice"],
                    "system_prompt": spec["prompt"],
                    "language": "en",
                },
            )
            agents.append(agent)
        return agents

    def _calls(self, agents: list[Agent]) -> list[CallLog]:
        """Generate sample inbound/outbound call logs."""
        live = [a for a in agents if a.status == "live"]
        if not live:
            return []

        # Remove previous demo call logs for these agents
        CallLog.objects.filter(agent__in=agents).delete()

        now = timezone.now()
        calls = []
        for i in range(36):
            agent = live[i % len(live)]
            day_offset = random.randint(0, 28)
            hour = random.choice([8, 9, 10, 11, 12, 13, 17, 18, 19, 20, 21, 22])
            started = now - timedelta(days=day_offset, hours=random.randint(0, 5))
            started = started.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
            duration = random.randint(45, 420)
            ended = started + timedelta(seconds=duration)

            roll = random.random()
            if roll < 0.42:
                outcome = "booked"
            elif roll < 0.72:
                outcome = "faq_resolved"
            else:
                outcome = "no_outcome"

            status = "completed" if random.random() > 0.08 else random.choice(["no-answer", "failed", "busy"])
            if status != "completed":
                outcome = "no_outcome"
                duration = random.randint(5, 40)

            sentiment = round(random.uniform(-0.2, 0.85), 2)
            if outcome == "booked":
                sentiment = round(random.uniform(0.25, 0.9), 2)

            guest_name, _ = GUEST_NAMES[i % len(GUEST_NAMES)]
            call = CallLog.objects.create(
                agent=agent,
                twilio_call_sid=f"CA{uuid.uuid4().hex}",
                caller_phone=PHONES[i % len(PHONES)],
                direction=random.choice(["inbound", "inbound", "inbound", "outbound"]),
                status=status,
                outcome=outcome,
                reason=random.choice(INTENTS),
                duration_seconds=duration,
                sentiment_score=sentiment,
                was_transferred=random.random() < 0.08,
                recording_url="",
                started_at=started,
                ended_at=ended if status == "completed" else None,
            )
            CallLog.objects.filter(pk=call.pk).update(created_at=started)
            call.refresh_from_db()
            calls.append(call)
        return calls

    def _transcripts(self, calls: list[CallLog]) -> None:
        """Attach a short sample transcript to recent calls."""
        sample = [c for c in calls if c.status == "completed"][:10]
        for call in sample:
            base = call.started_at or timezone.now()
            for idx, (speaker, text) in enumerate(TRANSCRIPTS):
                CallTranscript.objects.create(
                    call=call,
                    speaker=speaker,
                    text=text,
                    langgraph_node="",
                    timestamp=base + timedelta(seconds=12 * idx),
                )

    def _bookings(self, agents: list[Agent], calls: list[CallLog]) -> int:
        """Seed room and table bookings for the dashboard."""
        Booking.objects.filter(agent__in=agents).delete()
        live = [a for a in agents if a.status == "live"]
        today = date.today()
        booked_calls = [c for c in calls if c.outcome == "booked"]
        count = 0

        # Today’s reservations for dashboard panel
        for i in range(5):
            name, email = GUEST_NAMES[i]
            agent = live[i % len(live)]
            is_room = i % 2 == 0
            Booking.objects.create(
                agent=agent,
                call_sid=booked_calls[i].twilio_call_sid if i < len(booked_calls) else "",
                booking_type="room" if is_room else "table",
                guest_name=name,
                guest_email=email,
                guests=random.randint(1, 4) if is_room else random.randint(2, 6),
                check_in=today,
                check_out=today + timedelta(days=random.randint(1, 3)) if is_room else None,
                is_confirmed=i < 3,
                confirmed_at=timezone.now() - timedelta(hours=i) if i < 3 else None,
            )
            count += 1

        # Spread across the month
        for i in range(18):
            name, email = GUEST_NAMES[(i + 5) % len(GUEST_NAMES)]
            agent = live[i % len(live)]
            is_room = i % 3 != 0
            check_in = today + timedelta(days=random.randint(-12, 14))
            created = timezone.now() - timedelta(days=random.randint(0, 25), hours=random.randint(0, 20))
            sid = ""
            if i < len(booked_calls):
                sid = booked_calls[i].twilio_call_sid
            b = Booking.objects.create(
                agent=agent,
                call_sid=sid,
                booking_type="room" if is_room else "table",
                guest_name=name,
                guest_email=email,
                guests=random.randint(1, 5) if is_room else random.randint(2, 8),
                check_in=check_in,
                check_out=(check_in + timedelta(days=random.randint(1, 4))) if is_room else None,
                is_confirmed=random.random() > 0.25,
                confirmed_at=created if random.random() > 0.25 else None,
            )
            Booking.objects.filter(pk=b.pk).update(created_at=created)
            count += 1
        return count
