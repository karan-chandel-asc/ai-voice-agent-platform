"""Post-call Celery tasks dispatched from FastAPI via Redis queue."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.development")
django.setup()

from celery import shared_task
from django.conf import settings


@shared_task
def post_call_pipeline(call_sid: str, call_status: str, duration: int):
    """Runs after every call: save transcript, sentiment, CRM sync, SMS."""
    from calls.models import CallLog
    try:
        call = CallLog.objects.get(twilio_call_sid=call_sid)
        call.status = call_status
        call.duration_seconds = duration
        call.save(update_fields=["status", "duration_seconds"])
        analyze_sentiment.delay(str(call.id))
    except CallLog.DoesNotExist:
        pass


@shared_task
def analyze_sentiment(call_id: str):
    import json, re
    from groq import Groq
    from calls.models import CallLog
    from voice_engine.routers.prompts import SENTIMENT_SYSTEM_PROMPT
    call = CallLog.objects.get(id=call_id)
    transcripts = call.transcripts.all()
    if not transcripts:
        return
    full_text = "\n".join([f"{t.speaker}: {t.text}" for t in transcripts])
    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SENTIMENT_SYSTEM_PROMPT},
            {"role": "user", "content": full_text},
        ],
        max_tokens=60,
        temperature=0,
    )
    raw = (response.choices[0].message.content or "").strip()
    if not raw:
        return
    # strip markdown code fences if model wrapped the JSON
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw).strip()
    try:
        result = json.loads(raw)
        score = float(result.get("score", 0))
        # clamp to [-1, 1]
        call.sentiment_score = max(-1.0, min(1.0, score))
        call.save(update_fields=["sentiment_score"])
    except (json.JSONDecodeError, ValueError, KeyError):
        pass