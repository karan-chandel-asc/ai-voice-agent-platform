"""Retell AI client helpers: voices, languages, phones, agent create/bind."""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from django.utils import timezone
from retell import Retell

_BASE = Path(__file__).resolve().parent.parent
if str(_BASE) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_BASE))

load_dotenv(_BASE / ".env")

from core.logger import logger  # noqa: E402


# Official Retell create-agent Language enum (no list-languages API).
RETELL_LANGUAGE_CATALOG = [
    ("en-US", "English (US)"),
    ("en-IN", "English (India)"),
    ("en-GB", "English (UK)"),
    ("en-AU", "English (Australia)"),
    ("en-NZ", "English (New Zealand)"),
    ("de-DE", "German"),
    ("es-ES", "Spanish (Spain)"),
    ("es-419", "Spanish (Latin America)"),
    ("hi-IN", "Hindi"),
    ("fr-FR", "French"),
    ("fr-CA", "French (Canada)"),
    ("ja-JP", "Japanese"),
    ("pt-PT", "Portuguese"),
    ("pt-BR", "Portuguese (Brazil)"),
    ("zh-CN", "Chinese (Mandarin)"),
    ("ru-RU", "Russian"),
    ("it-IT", "Italian"),
    ("ko-KR", "Korean"),
    ("nl-NL", "Dutch"),
    ("nl-BE", "Dutch (Belgium)"),
    ("pl-PL", "Polish"),
    ("tr-TR", "Turkish"),
    ("vi-VN", "Vietnamese"),
    ("ro-RO", "Romanian"),
    ("bg-BG", "Bulgarian"),
    ("ca-ES", "Catalan"),
    ("th-TH", "Thai"),
    ("da-DK", "Danish"),
    ("fi-FI", "Finnish"),
    ("el-GR", "Greek"),
    ("hu-HU", "Hungarian"),
    ("id-ID", "Indonesian"),
    ("no-NO", "Norwegian"),
    ("sk-SK", "Slovak"),
    ("sv-SE", "Swedish"),
    ("lt-LT", "Lithuanian"),
    ("lv-LV", "Latvian"),
    ("cs-CZ", "Czech"),
    ("ms-MY", "Malay"),
    ("af-ZA", "Afrikaans"),
    ("ar-SA", "Arabic"),
    ("az-AZ", "Azerbaijani"),
    ("bs-BA", "Bosnian"),
    ("cy-GB", "Welsh"),
    ("fa-IR", "Persian"),
    ("fil-PH", "Filipino"),
    ("gl-ES", "Galician"),
    ("he-IL", "Hebrew"),
    ("hr-HR", "Croatian"),
    ("hy-AM", "Armenian"),
    ("is-IS", "Icelandic"),
    ("kk-KZ", "Kazakh"),
    ("kn-IN", "Kannada"),
    ("mk-MK", "Macedonian"),
    ("mr-IN", "Marathi"),
    ("ne-NP", "Nepali"),
    ("sl-SI", "Slovenian"),
    ("sr-RS", "Serbian"),
    ("sw-KE", "Swahili"),
    ("ta-IN", "Tamil"),
    ("ur-IN", "Urdu"),
    ("yue-CN", "Cantonese"),
    ("uk-UA", "Ukrainian"),
]


class RetellServices:
    def __init__(self):
        # Windows often fails SSL CA verify against Retell; disable verify locally.
        self.retell = Retell(
            api_key=os.getenv("retell_api_key"),
            http_client=httpx.Client(verify=False, timeout=60.0),
        )

    def get_retell_voices_list(self):
        try:
            voices = self.retell.voice.list()
            return voices, "Voices fetched successfully"
        except Exception as e:
            logger.error(f"RetellServices: Failed to fetch voices: {e}", exc_info=True)
            return None, "Failed to fetch voices"

    def sync_voices_to_db(self):
        """Fetch Retell voices and upsert into ElevenLabsVoices."""
        from agents.models import ElevenLabsVoices

        voices, err = self.get_retell_voices_list()
        if voices is None:
            return None, err or "Failed to fetch voices from Retell"

        created = updated = 0
        try:
            for v in voices:
                voice_id = getattr(v, "voice_id", None) or ""
                if not voice_id:
                    continue
                name = (getattr(v, "voice_name", None) or voice_id)[:100]
                preview = getattr(v, "preview_audio_url", None) or ""
                obj, was_created = ElevenLabsVoices.objects.update_or_create(
                    voice_id=voice_id,
                    defaults={
                        "name": name,
                        "recording_url": preview or None,
                        "is_active": True,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            return {
                "created": created,
                "updated": updated,
                "total": created + updated,
            }, "Voices synced from Retell successfully"
        except Exception as e:
            logger.error(f"RetellServices: Failed to sync voices: {e}", exc_info=True)
            return None, "Failed to save voices"

    def sync_languages_to_db(self):
        """Upsert Retell locale catalog (Retell has no list-languages endpoint)."""
        from agents.models import RetellLanguage

        created = updated = 0
        try:
            for code, label in RETELL_LANGUAGE_CATALOG:
                obj, was_created = RetellLanguage.objects.update_or_create(
                    code=code,
                    defaults={"label": label, "is_active": True},
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            return {
                "created": created,
                "updated": updated,
                "total": created + updated,
            }, "Languages synced from Retell catalog successfully"
        except Exception as e:
            logger.error(f"RetellServices: Failed to sync languages: {e}", exc_info=True)
            return None, "Failed to save languages"

    def _iter_phone_pages(self):
        """Yield phone number objects across Retell pagination."""
        pagination_key = None
        while True:
            kwargs = {"limit": 100}
            if pagination_key:
                kwargs["pagination_key"] = pagination_key
            page = self.retell.phone_number.list(**kwargs)
            items = getattr(page, "items", None)
            if items is None:
                # Older SDK may return a bare list
                items = page if isinstance(page, list) else []
            for item in items:
                yield item
            has_more = bool(getattr(page, "has_more", False))
            pagination_key = getattr(page, "pagination_key", None)
            if not has_more or not pagination_key:
                break

    def sync_phone_numbers_to_db(self):
        """Pull Retell phone numbers + seed Twilio numbers from env."""
        from agents.models import RetellPhoneNumber
        from django.conf import settings as dj_settings

        created = updated = 0
        now = timezone.now()
        try:
            seen = set()
            for p in self._iter_phone_pages():
                number = getattr(p, "phone_number", None) or ""
                if not number:
                    continue
                seen.add(number)
                inbound = getattr(p, "inbound_agents", None) or []
                inbound_id = ""
                if inbound:
                    first = inbound[0]
                    inbound_id = getattr(first, "agent_id", None) or (
                        first.get("agent_id") if isinstance(first, dict) else ""
                    ) or ""
                obj, was_created = RetellPhoneNumber.objects.update_or_create(
                    phone_number=number,
                    defaults={
                        "phone_number_pretty": getattr(p, "phone_number_pretty", "") or number,
                        "nickname": getattr(p, "nickname", "") or "",
                        "phone_number_type": getattr(p, "phone_number_type", "") or "",
                        "inbound_retell_agent_id": inbound_id or "",
                        "is_active": True,
                        "last_synced_at": now,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

            # Seed local Twilio numbers from .env so UI can assign 1:1
            env_numbers = []
            for raw in [
                getattr(dj_settings, "TWILIO_PHONE_NUMBER", "") or os.getenv("TWILIO_PHONE_NUMBER", ""),
                getattr(dj_settings, "TWILIO_PHONE_NUMBER_2", "") or os.getenv("twilio_number", ""),
            ]:
                n = (raw or "").strip().strip('"')
                if n and n not in seen:
                    env_numbers.append(n)

            for i, number in enumerate(env_numbers, start=1):
                obj, was_created = RetellPhoneNumber.objects.update_or_create(
                    phone_number=number,
                    defaults={
                        "phone_number_pretty": number,
                        "nickname": f"Twilio number {i}",
                        "phone_number_type": "twilio-env",
                        "is_active": True,
                        "last_synced_at": now,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

            return {
                "created": created,
                "updated": updated,
                "total": RetellPhoneNumber.objects.filter(is_active=True).count(),
                "retell_count": len(seen),
            }, "Phone numbers synced successfully"
        except Exception as e:
            logger.error(f"RetellServices: Failed to sync phones: {e}", exc_info=True)
            return None, "Failed to sync phone numbers"

    def create_retell_agent(self, *, agent_name, system_prompt, voice_id, language="en-US"):
        """Create Retell LLM + voice agent and publish draft version."""
        try:
            try:
                self.retell.voice.retrieve(voice_id)
            except Exception:
                return None, (
                    f"Voice '{voice_id}' is not available in Retell. "
                    "Sync My Voices again and choose another voice."
                )

            prompt = (system_prompt or "").strip() or f"You are {agent_name}, a helpful voice agent."
            llm = self.retell.llm.create(
                general_prompt=prompt,
                begin_message=f"Hi, this is {agent_name}. How can I help you today?",
                start_speaker="agent",
            )
            agent = self.retell.agent.create(
                agent_name=agent_name,
                response_engine={"type": "retell-llm", "llm_id": llm.llm_id},
                voice_id=voice_id,
                language=language or "en-US",
            )
            version = getattr(agent, "version", 0)
            try:
                self.retell.agent.publish(agent_id=agent.agent_id, version=version)
            except Exception as pub_err:
                logger.warning(f"Retell publish warning for {agent.agent_id}: {pub_err}")

            return {
                "retell_agent_id": agent.agent_id,
                "retell_llm_id": llm.llm_id,
                "version": version,
                "tools_count": 1,
                "tools_data": [{
                    "name": "end_call",
                    "type": "end_call",
                    "description": "End the call when the user is done.",
                }],
            }, "Retell agent created successfully"
        except Exception as e:
            logger.error(f"RetellServices: create_retell_agent failed: {e}", exc_info=True)
            return None, f"Failed to create Retell agent: {e}"

    def update_retell_agent(self, *, retell_agent_id, retell_llm_id, agent_name=None,
                            system_prompt=None, voice_id=None, language=None):
        """Update Retell LLM prompt and/or agent voice settings."""
        try:
            if retell_llm_id and system_prompt is not None:
                self.retell.llm.update(
                    llm_id=retell_llm_id,
                    general_prompt=system_prompt,
                )
            payload = {}
            if agent_name is not None:
                payload["agent_name"] = agent_name
            if voice_id is not None:
                payload["voice_id"] = voice_id
            if language is not None:
                payload["language"] = language
            if payload and retell_agent_id:
                updated = self.retell.agent.update(agent_id=retell_agent_id, **payload)
                version = getattr(updated, "version", None)
                if version is not None:
                    try:
                        self.retell.agent.publish(agent_id=retell_agent_id, version=version)
                    except Exception as pub_err:
                        logger.warning(f"Retell publish warning on update: {pub_err}")
            return True, "Retell agent updated successfully"
        except Exception as e:
            logger.error(f"RetellServices: update_retell_agent failed: {e}", exc_info=True)
            return None, f"Failed to update Retell agent: {e}"

    def delete_retell_agent(self, *, retell_agent_id="", retell_llm_id=""):
        try:
            if retell_agent_id:
                self.retell.agent.delete(agent_id=retell_agent_id)
            if retell_llm_id:
                try:
                    self.retell.llm.delete(llm_id=retell_llm_id)
                except Exception:
                    pass
            return True, "Retell agent deleted"
        except Exception as e:
            logger.error(f"RetellServices: delete_retell_agent failed: {e}", exc_info=True)
            return None, f"Failed to delete Retell agent: {e}"

    def list_retell_agent_ids(self):
        """Return set of all Retell agent_id values (paginated)."""
        try:
            ids = set()
            pagination_key = None
            while True:
                kwargs = {"limit": 100}
                if pagination_key:
                    kwargs["pagination_key"] = pagination_key
                page = self.retell.agent.list(**kwargs)
                items = getattr(page, "items", None)
                if items is None:
                    items = page if isinstance(page, list) else []
                for a in items:
                    aid = getattr(a, "agent_id", None) or ""
                    if aid:
                        ids.add(aid)
                has_more = bool(getattr(page, "has_more", False))
                pagination_key = getattr(page, "pagination_key", None)
                if not has_more or not pagination_key:
                    break
            return ids, "Retell agents listed successfully"
        except Exception as e:
            logger.error(f"RetellServices: list_retell_agent_ids failed: {e}", exc_info=True)
            return None, f"Failed to list Retell agents: {e}"

    def _to_dict(self, obj):
        if obj is None:
            return {}
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        if isinstance(obj, dict):
            return obj
        return {}

    def fetch_retell_agent_details(self, agent_id):
        """
        Pull full agent + linked LLM (prompt/tools) from Retell.
        Returns a normalized dict for DB upsert.
        """
        try:
            agent = self.retell.agent.retrieve(agent_id)
            agent_data = self._to_dict(agent)
            response_engine = agent_data.get("response_engine") or {}
            llm_id = ""
            llm_data = {}
            tools = []
            prompt = ""
            begin_message = ""

            if isinstance(response_engine, dict):
                llm_id = response_engine.get("llm_id") or ""
                engine_type = response_engine.get("type") or ""
            else:
                llm_id = getattr(response_engine, "llm_id", "") or ""
                engine_type = getattr(response_engine, "type", "") or ""

            if llm_id and engine_type in ("", "retell-llm", "retell_llm"):
                try:
                    llm = self.retell.llm.retrieve(llm_id)
                    llm_data = self._to_dict(llm)
                    tools = llm_data.get("general_tools") or []
                    if not isinstance(tools, list):
                        tools = []
                    prompt = llm_data.get("general_prompt") or ""
                    begin_message = llm_data.get("begin_message") or ""
                except Exception as llm_err:
                    logger.warning(f"Retell LLM retrieve failed for {llm_id}: {llm_err}")

            # Normalize tools to plain dicts
            normalized_tools = []
            for t in tools:
                if hasattr(t, "model_dump"):
                    td = t.model_dump()
                elif isinstance(t, dict):
                    td = t
                else:
                    td = {
                        "name": getattr(t, "name", ""),
                        "type": getattr(t, "type", ""),
                        "description": getattr(t, "description", "") or "",
                    }
                normalized_tools.append({
                    "name": td.get("name") or "",
                    "type": td.get("type") or "",
                    "description": td.get("description") or "",
                })

            language = agent_data.get("language") or "en-US"
            if isinstance(language, list):
                language = language[0] if language else "en-US"

            return {
                "retell_agent_id": agent_data.get("agent_id") or agent_id,
                "agent_name": (agent_data.get("agent_name") or "Untitled Agent")[:100],
                "retell_llm_id": llm_id or "",
                "retell_voice_id": agent_data.get("voice_id") or "",
                "language": str(language)[:20],
                "system_prompt": prompt or "",
                "begin_message": begin_message or "",
                "retell_version": agent_data.get("version"),
                "is_published": bool(agent_data.get("is_published")),
                "channel": (agent_data.get("channel") or "voice")[:40],
                "tools_count": len(normalized_tools),
                "tools_data": normalized_tools,
                "retell_snapshot": {
                    "agent": agent_data,
                    "llm": llm_data,
                },
            }, "Agent details fetched"
        except Exception as e:
            logger.error(f"RetellServices: fetch_retell_agent_details failed: {e}", exc_info=True)
            return None, f"Failed to fetch agent {agent_id}: {e}"

    def list_retell_agents_full(self):
        """List all Retell agents then retrieve full details (+ tools) for each."""
        ids, msg = self.list_retell_agent_ids()
        if ids is None:
            return None, msg
        details = []
        errors = []
        for aid in ids:
            data, err = self.fetch_retell_agent_details(aid)
            if data is None:
                errors.append({"agent_id": aid, "error": err})
                continue
            details.append(data)
        return {
            "agents": details,
            "errors": errors,
            "total": len(details),
        }, "Retell agents fetched successfully"

    def bind_phone_to_agent(self, phone_number, retell_agent_id):
        """Bind inbound (and outbound) traffic on a Retell number to one agent."""
        try:
            agents = [{"agent_id": retell_agent_id, "weight": 1}]
            self.retell.phone_number.update(
                phone_number=phone_number,
                inbound_agents=agents,
                outbound_agents=agents,
            )
            return True, "Phone number bound to agent"
        except Exception as e:
            logger.error(f"RetellServices: bind_phone failed: {e}", exc_info=True)
            return None, (
                f"Failed to bind {phone_number} in Retell. "
                "Import this Twilio number into your Retell dashboard first, then sync phones. "
                f"Details: {e}"
            )

    def unbind_phone(self, phone_number):
        try:
            self.retell.phone_number.update(
                phone_number=phone_number,
                inbound_agents=[],
                outbound_agents=[],
            )
            return True, "Phone unbound"
        except Exception as e:
            logger.warning(f"RetellServices: unbind_phone warning: {e}")
            return None, str(e)


retell_services = RetellServices()
