from django.db import transaction
from django.db.models import Q
from .models import Agent, ElevenLabsVoices, RetellLanguage, RetellPhoneNumber
from .retell_services import retell_services


class ElevenLabsVoicesMechanism:
    def get_all_ElevenLabs_voices(self):
        try:
            voices = ElevenLabsVoices.objects.filter(is_active=True).order_by("name")
            return voices, "ElevenLabsVoices fetched successfully"
        except Exception as e:
            return None, f"Error fetching ElevenLabsVoices: {e}"

    def get_elevenVoice_by_voice_id(self, voice_id):
        try:
            voice = ElevenLabsVoices.objects.get(id=voice_id)
            return voice, "ElevenLabsVoices fetched successfully"
        except ElevenLabsVoices.DoesNotExist:
            return None, "Voice not found"
        except Exception as e:
            return None, f"Error fetching ElevenLabsVoices: {e}"


class RetellLanguageMechanism:
    def get_all(self, search=None):
        try:
            qs = RetellLanguage.objects.filter(is_active=True).order_by("label")
            if search:
                qs = qs.filter(Q(code__icontains=search) | Q(label__icontains=search))
            return qs, "Languages fetched successfully"
        except Exception as e:
            return None, f"Error fetching languages: {e}"


class RetellPhoneMechanism:
    def get_all(self, available_only=False, search=None):
        try:
            qs = RetellPhoneNumber.objects.filter(is_active=True).select_related("assigned_agent")
            if available_only:
                qs = qs.filter(assigned_agent__isnull=True)
            if search:
                qs = qs.filter(
                    Q(phone_number__icontains=search)
                    | Q(phone_number_pretty__icontains=search)
                    | Q(nickname__icontains=search)
                )
            return qs.order_by("phone_number"), "Phone numbers fetched successfully"
        except Exception as e:
            return None, f"Error fetching phones: {e}"


class AgentMechanism:
    def _claim_phone(self, agent, phone_number, retell_agent_id):
        phone_number = (phone_number or "").strip()
        if not phone_number:
            return True, ""

        conflict = Agent.objects.filter(phone_number=phone_number).exclude(pk=agent.pk).first()
        if conflict:
            return None, f"Phone {phone_number} is already assigned to {conflict.agent_name}"

        phone_row = RetellPhoneNumber.objects.filter(phone_number=phone_number).first()
        if phone_row and phone_row.assigned_agent_id and phone_row.assigned_agent_id != agent.pk:
            return None, f"Phone {phone_number} is already assigned to another agent"

        if retell_agent_id:
            ok, msg = retell_services.bind_phone_to_agent(phone_number, retell_agent_id)
            if ok is None:
                return None, msg

        agent.phone_number = phone_number
        agent.save(update_fields=["phone_number", "updated_at"])

        phone_row, _ = RetellPhoneNumber.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                "phone_number_pretty": phone_number,
                "nickname": "",
                "phone_number_type": "assigned",
                "is_active": True,
            },
        )
        phone_row.assigned_agent = agent
        phone_row.inbound_retell_agent_id = retell_agent_id or ""
        phone_row.save(update_fields=["assigned_agent", "inbound_retell_agent_id"])
        return True, "Phone assigned"

    def _release_phone(self, agent, unbind_retell=True):
        old = (agent.phone_number or "").strip()
        if not old:
            return
        if unbind_retell:
            retell_services.unbind_phone(old)
        RetellPhoneNumber.objects.filter(phone_number=old, assigned_agent=agent).update(
            assigned_agent=None,
            inbound_retell_agent_id="",
        )
        agent.phone_number = ""
        agent.save(update_fields=["phone_number", "updated_at"])

    def create_agent(self, user, data):
        try:
            if not data.elevenlabs_voice_id:
                return None, "Voice is required to create a Retell agent"

            voice, _ = ElevenLabsVoicesMechanism().get_elevenVoice_by_voice_id(data.elevenlabs_voice_id)
            if not voice:
                return None, "Voice not found. Sync voices from Retell first."

            language = (data.language or "en-US").strip() or "en-US"
            phone = (data.phone_number or "").strip()

            if phone:
                taken = Agent.objects.filter(phone_number=phone).exists()
                if taken:
                    return None, f"Phone {phone} is already assigned to another agent"

            retell_data, retell_msg = retell_services.create_retell_agent(
                agent_name=data.agent_name,
                system_prompt=data.system_prompt or "",
                voice_id=voice.voice_id,
                language=language,
            )
            if retell_data is None:
                return None, retell_msg

            with transaction.atomic():
                agent = Agent.objects.create(
                    owner=user,
                    agent_name=data.agent_name,
                    system_prompt=data.system_prompt or "",
                    language=language,
                    status="live",
                    elevenlabs_voice=voice,
                    retell_agent_id=retell_data["retell_agent_id"],
                    retell_llm_id=retell_data["retell_llm_id"],
                    retell_voice_id=voice.voice_id,
                    retell_voice_name=voice.name,
                    retell_version=retell_data.get("version"),
                    is_published=True,
                    tools_count=int(retell_data.get("tools_count") or 0),
                    tools_data=retell_data.get("tools_data") or [],
                )

                if phone:
                    ok, msg = self._claim_phone(agent, phone, agent.retell_agent_id)
                    if ok is None:
                        # Roll back local + Retell agent so user can retry cleanly
                        transaction.set_rollback(True)
                        retell_services.delete_retell_agent(
                            retell_agent_id=retell_data["retell_agent_id"],
                            retell_llm_id=retell_data["retell_llm_id"],
                        )
                        return None, msg

            return agent, "Agent created on Retell successfully"
        except Exception as e:
            return None, f"Error creating agent: {e}"

    def update_agent(self, agent_id, user, data):
        try:
            agent = Agent.objects.select_related("elevenlabs_voice").get(id=agent_id, owner=user)
            update_fields = []
            voice_retell_id = agent.elevenlabs_voice.voice_id if agent.elevenlabs_voice else None

            if data.agent_name is not None:
                agent.agent_name = data.agent_name
                update_fields.append("agent_name")

            if data.system_prompt is not None:
                agent.system_prompt = data.system_prompt
                update_fields.append("system_prompt")

            if data.language is not None:
                agent.language = data.language
                update_fields.append("language")

            if data.elevenlabs_voice_id is not None:
                if data.elevenlabs_voice_id:
                    voice, _ = ElevenLabsVoicesMechanism().get_elevenVoice_by_voice_id(data.elevenlabs_voice_id)
                    if voice:
                        agent.elevenlabs_voice = voice
                        voice_retell_id = voice.voice_id
                        update_fields.append("elevenlabs_voice")
                else:
                    agent.elevenlabs_voice = None
                    update_fields.append("elevenlabs_voice")

            if update_fields:
                update_fields.append("updated_at")
                agent.save(update_fields=update_fields)

            if agent.retell_agent_id:
                retell_services.update_retell_agent(
                    retell_agent_id=agent.retell_agent_id,
                    retell_llm_id=agent.retell_llm_id,
                    agent_name=agent.agent_name if data.agent_name is not None else None,
                    system_prompt=agent.system_prompt if data.system_prompt is not None else None,
                    voice_id=voice_retell_id if data.elevenlabs_voice_id is not None else None,
                    language=agent.language if data.language is not None else None,
                )
            elif data.elevenlabs_voice_id and agent.elevenlabs_voice:
                # Local-only agent: create on Retell now
                retell_data, msg = retell_services.create_retell_agent(
                    agent_name=agent.agent_name,
                    system_prompt=agent.system_prompt,
                    voice_id=agent.elevenlabs_voice.voice_id,
                    language=agent.language or "en-US",
                )
                if retell_data:
                    agent.retell_agent_id = retell_data["retell_agent_id"]
                    agent.retell_llm_id = retell_data["retell_llm_id"]
                    agent.save(update_fields=["retell_agent_id", "retell_llm_id", "updated_at"])

            if data.phone_number is not None:
                new_phone = (data.phone_number or "").strip()
                old_phone = (agent.phone_number or "").strip()
                if new_phone != old_phone:
                    if old_phone:
                        self._release_phone(agent, unbind_retell=True)
                    if new_phone:
                        if not agent.retell_agent_id:
                            return None, "Create/sync Retell agent before assigning a phone number"
                        ok, msg = self._claim_phone(agent, new_phone, agent.retell_agent_id)
                        if ok is None:
                            return None, msg

            return agent, "Agent updated successfully"
        except Agent.DoesNotExist:
            return None, "Agent not found"
        except Exception as e:
            return None, f"Error updating agent: {e}"

    def get_agent_by_id(self, agent_id, user):
        try:
            agent = (
                Agent.objects
                .select_related("owner", "elevenlabs_voice")
                .get(id=agent_id, owner=user)
            )
            return agent, "Agent fetched successfully"
        except Agent.DoesNotExist:
            return None, "Agent not found"
        except Exception as e:
            return None, f"Error fetching agent: {e}"

    def delete_agent(self, agent_id, user):
        try:
            agent = Agent.objects.get(id=agent_id, owner=user)
            if agent.phone_number:
                self._release_phone(agent, unbind_retell=True)
            if agent.retell_agent_id or agent.retell_llm_id:
                retell_services.delete_retell_agent(
                    retell_agent_id=agent.retell_agent_id,
                    retell_llm_id=agent.retell_llm_id,
                )
            agent.delete()
            return True, "Agent deleted successfully"
        except Agent.DoesNotExist:
            return None, "Agent not found"
        except Exception as e:
            return None, f"Error deleting agent: {e}"

    def get_all_agents(self, user, search=None):
        try:
            agents = (
                Agent.objects
                .filter(owner=user)
                .select_related("owner", "elevenlabs_voice")
                .order_by("-created_at")
            )
            if search:
                agents = agents.filter(
                    Q(agent_name__icontains=search) | Q(phone_number__icontains=search)
                )
            return agents, "Agents fetched successfully"
        except Exception as e:
            return None, f"Error fetching agents: {e}"

    def delete_all_agents(self, user):
        try:
            agents = list(Agent.objects.filter(owner=user))
            for agent in agents:
                if agent.phone_number:
                    self._release_phone(agent, unbind_retell=True)
                if agent.retell_agent_id or agent.retell_llm_id:
                    retell_services.delete_retell_agent(
                        retell_agent_id=agent.retell_agent_id,
                        retell_llm_id=agent.retell_llm_id,
                    )
            deleted, _ = Agent.objects.filter(owner=user).delete()
            return deleted, "All agents deleted successfully"
        except Exception as e:
            return None, f"Error deleting agents: {e}"

    def sync_agents_with_retell(self, user):
        """
        Full sync with Retell:
        - Upsert every Retell agent into local DB (prompt, voice, tools, snapshot)
        - Delete local linked agents missing on Retell
        Local deletes already remove the Retell agent.
        """
        from django.utils import timezone

        try:
            payload, msg = retell_services.list_retell_agents_full()
            if payload is None:
                return None, msg

            details = payload.get("agents") or []
            retell_ids = {d["retell_agent_id"] for d in details if d.get("retell_agent_id")}
            now = timezone.now()
            created = updated = 0
            synced = []

            for d in details:
                rid = d["retell_agent_id"]
                voice = None
                voice_id = d.get("retell_voice_id") or ""
                if voice_id:
                    voice = ElevenLabsVoices.objects.filter(voice_id=voice_id).first()

                voice_name = ""
                if voice:
                    voice_name = voice.name
                else:
                    # Prefer name from list snapshot if present later
                    snap_agent = (d.get("retell_snapshot") or {}).get("agent") or {}
                    voice_name = (snap_agent.get("voice_name") or voice_id or "")[:100]

                defaults = {
                    "agent_name": d.get("agent_name") or "Untitled Agent",
                    "system_prompt": d.get("system_prompt") or "",
                    "language": d.get("language") or "en-US",
                    "retell_llm_id": d.get("retell_llm_id") or "",
                    "retell_voice_id": voice_id,
                    "retell_voice_name": voice_name,
                    "retell_version": d.get("retell_version"),
                    "is_published": bool(d.get("is_published")),
                    "channel": d.get("channel") or "voice",
                    "tools_count": int(d.get("tools_count") or 0),
                    "tools_data": d.get("tools_data") or [],
                    "retell_snapshot": d.get("retell_snapshot") or {},
                    "last_synced_at": now,
                    "status": "live",
                }
                if voice:
                    defaults["elevenlabs_voice"] = voice

                agent = Agent.objects.filter(owner=user, retell_agent_id=rid).first()
                if agent is None:
                    # Also match orphaned same retell id under this user created earlier
                    agent = Agent.objects.filter(retell_agent_id=rid, owner=user).first()

                if agent:
                    for k, v in defaults.items():
                        setattr(agent, k, v)
                    agent.save()
                    updated += 1
                    action = "updated"
                else:
                    agent = Agent.objects.create(
                        owner=user,
                        retell_agent_id=rid,
                        **defaults,
                    )
                    created += 1
                    action = "created"

                synced.append({
                    "agent_id": str(agent.id),
                    "retell_agent_id": rid,
                    "agent_name": agent.agent_name,
                    "tools_count": agent.tools_count,
                    "action": action,
                })

            # Remove local Retell-linked agents that no longer exist remotely
            deleted_local = []
            linked = Agent.objects.filter(owner=user).exclude(retell_agent_id="")
            for agent in linked:
                if agent.retell_agent_id not in retell_ids:
                    name = agent.agent_name
                    rid = agent.retell_agent_id
                    if agent.phone_number:
                        self._release_phone(agent, unbind_retell=False)
                    agent.delete()
                    deleted_local.append({"agent_name": name, "retell_agent_id": rid})

            return {
                "retell_agents": len(retell_ids),
                "created": created,
                "updated": updated,
                "deleted_local": len(deleted_local),
                "deleted_agents": deleted_local,
                "synced_agents": synced,
                "fetch_errors": payload.get("errors") or [],
            }, "Agents synced from Retell successfully"
        except Exception as e:
            return None, f"Error syncing agents: {e}"
