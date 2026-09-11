"""Generate test-call question prompts from an agent's system prompt via Groq."""
import json
import logging
import re

from django.conf import settings

logger = logging.getLogger(__name__)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"


def _fallback_sections(agent_name: str, system_prompt: str) -> list[dict]:
    """Keyword-based fallback when Groq is unavailable."""
    text = (system_prompt or "").lower()
    name = agent_name or "the property"
    sections = []

    guest = [
        f"What can you help me with at {name}?",
        "What are your hours / check-in times?",
        "Do you have parking or Wi‑Fi for guests?",
    ]
    if any(k in text for k in ("amenit", "spa", "gym", "pool", "wifi", "wi-fi", "parking", "breakfast")):
        guest.append("Tell me about amenities available to guests.")
    sections.append({"title": "Guest questions", "prompts": guest[:4]})

    if any(k in text for k in ("room", "hotel", "check-in", "reservation", "suite", "deluxe", "stay")):
        sections.append({
            "title": "Hotel room booking",
            "prompts": [
                "Do you have a room available for tomorrow for 2 guests?",
                "How much would a room cost for 2 nights starting tomorrow?",
                "Please book a room for me from tomorrow for 2 nights. My name is Alex Rivera, phone +1 555 0100, email alex@example.com.",
            ],
        })

    if any(k in text for k in ("table", "restaurant", "dining", "dinner", "lunch", "cover", "party size")):
        sections.append({
            "title": "Restaurant / table",
            "prompts": [
                "Can I reserve a table for 4 people tomorrow at 7:30 PM?",
                "Is there availability for a party of 2 tonight at 8 PM?",
                "Please book a table for 4 tomorrow at 19:00 under Priya Sharma, phone +1 555 0199, email priya@example.com.",
            ],
        })

    if any(k in text for k in ("escalat", "manager", "human", "staff", "transfer", "lead")):
        sections.append({
            "title": "Escalation / staff",
            "prompts": [
                "I need to speak with a manager.",
                "Please leave my details for someone to call me back.",
            ],
        })

    if len(sections) == 1:
        sections.append({
            "title": "Try next",
            "prompts": [
                "Can you help me make a booking?",
                "What information do you need from me?",
            ],
        })

    return sections


def _extract_json(raw: str) -> dict | None:
    if not raw:
        return None
    raw = raw.strip()
    # Strip markdown fences if present
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _normalize_sections(payload) -> list[dict]:
    sections_in = []
    if isinstance(payload, dict):
        sections_in = payload.get("sections") or []
    elif isinstance(payload, list):
        sections_in = payload

    out = []
    for sec in sections_in:
        if not isinstance(sec, dict):
            continue
        title = (sec.get("title") or sec.get("category") or "Suggestions").strip()
        prompts = sec.get("prompts") or sec.get("questions") or sec.get("items") or []
        clean = []
        for p in prompts:
            if isinstance(p, str) and p.strip():
                clean.append(p.strip())
            elif isinstance(p, dict):
                q = (p.get("text") or p.get("question") or p.get("prompt") or "").strip()
                if q:
                    clean.append(q)
        if title and clean:
            out.append({"title": title, "prompts": clean[:6]})
    return out


def generate_test_prompts(*, agent_name: str, system_prompt: str) -> tuple[dict | None, str]:
    """
    Ask Groq to produce categorized guest utterances tailored to this agent's prompt.

    Returns (data, message) where data =
      { "sections": [ {"title": str, "prompts": [str, ...] }, ... ], "source": "groq"|"fallback" }
    """
    prompt = (system_prompt or "").strip()
    name = (agent_name or "Voice Agent").strip()

    if not prompt:
        return {
            "sections": _fallback_sections(name, ""),
            "source": "fallback",
            "notes": "No system prompt on this agent — showing generic suggestions.",
        }, "Generated with fallback"

    api_key = (getattr(settings, "GROQ_API_KEY", None) or "").strip().strip('"')
    if not api_key:
        logger.warning("[GROQ] GROQ_API_KEY missing — using fallback prompts")
        return {
            "sections": _fallback_sections(name, prompt),
            "source": "fallback",
            "notes": "Groq API key not configured.",
        }, "Generated with fallback"

    system = (
        "You help QA testers exercise a hospitality voice agent. "
        "Read the agent's system prompt and invent realistic things a CALLER would SAY aloud. "
        "Return ONLY valid JSON with this shape:\n"
        '{"sections":[{"title":"Category name","prompts":["utterance 1","utterance 2"]}],'
        '"notes":"one short tip"}\n'
        "Rules:\n"
        "- Base categories and questions STRICTLY on what the agent prompt supports "
        "(FAQ, rooms, tables, leads, escalation, etc.). Do not invent unsupported tools.\n"
        "- Each section: 2–4 short spoken prompts (first person, natural speech).\n"
        "- Include concrete demo details when booking (name, phone, email, dates like tomorrow, party size).\n"
        "- Prefer 3–5 sections max. No markdown, no commentary outside JSON."
    )
    user = (
        f"Agent name: {name}\n\n"
        f"Agent system prompt:\n\"\"\"\n{prompt[:6000]}\n\"\"\""
    )

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        raw = (completion.choices[0].message.content or "").strip()
        parsed = _extract_json(raw)
        sections = _normalize_sections(parsed)
        if not sections:
            raise ValueError("Groq returned empty sections")

        notes = ""
        if isinstance(parsed, dict):
            notes = (parsed.get("notes") or "").strip()

        return {
            "sections": sections,
            "source": "groq",
            "notes": notes,
            "agent_name": name,
        }, "Test prompts generated"
    except Exception as e:
        logger.error(f"[GROQ] test prompt generation failed: {e}")
        return {
            "sections": _fallback_sections(name, prompt),
            "source": "fallback",
            "notes": "Could not reach Groq — showing prompt-based fallback suggestions.",
            "agent_name": name,
        }, "Generated with fallback"
