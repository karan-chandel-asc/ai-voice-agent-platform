from django.conf import settings
from .models import Agent, ElevenLabsVoice, AgentUserTool, PhoneNumber, UserTool, Booking
def provision_twilio_number(agent):
    """Purchase and assign a Twilio phone number to the agent."""
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        numbers = client.available_phone_numbers("US").local.list(limit=1)
        if numbers:
            purchased = client.incoming_phone_numbers.create(
                phone_number=numbers[0].phone_number,
                voice_url=f"{settings.FASTAPI_BASE_URL}/voice/inbound",
                status_callback=f"{settings.FASTAPI_BASE_URL}/voice/status",
            )
            agent.twilio_phone_number = purchased.phone_number
            agent.status = "live"
            agent.save(update_fields=["twilio_phone_number", "status"])
    except Exception as e:
        agent.status = "error"
        agent.save(update_fields=["status"])
        raise e


class ElevenLabsVoiceMechanism:
    def get_all_ElevenLabs_voices(self):
        try:
            voices = ElevenLabsVoice.objects.all()
            return voices, "ElevenLabsVoices fetched successfully"
        except Exception as e:
            return None, f"Error fetching ElevenLabsVoices: {e}"

    def get_elevenVoice_by_voice_id(self, voice_id):
        try:
            voice = ElevenLabsVoice.objects.get(id=voice_id)
            return voice, "ElevenLabsVoice fetched successfully"
        except ElevenLabsVoice.DoesNotExist:
            return None, "Voice not found"
        except Exception as e:
            return None, f"Error fetching ElevenLabsVoice: {e}"



class AgentMechanism:
    def create_agent(self, user, data):
        from django.utils import timezone
        try:
            agent = Agent.objects.create(
                owner=user,
                agent_name=data.agent_name,
                system_prompt=data.system_prompt,
                language=data.language or "en",
                status="draft" if data.is_draft else "live",

            )

            if data.elevenlabs_voice_id:
                voice, _ = ElevenLabsVoiceMechanism().get_elevenVoice_by_voice_id(data.elevenlabs_voice_id)
                if voice:
                    agent.elevenlabs_voice = voice
                    agent.save(update_fields=["elevenlabs_voice"])

            if data.user_tools:
                for ut_id in data.user_tools:
                    try:
                        ut = UserTool.objects.get(id=ut_id, owner=user)
                        AgentUserTool.objects.create(agent=agent, user_tool=ut)
                    except UserTool.DoesNotExist:
                        pass

            if data.phone_number_id:
                phone, _ = PhoneNumberMechanism().get_phone_number_by_id(data.phone_number_id)
                if phone:
                    phone.agent       = agent
                    phone.status      = "active"
                    phone.assigned_at = timezone.now()
                    phone.save(update_fields=["agent", "status", "assigned_at"])

            return agent, "Agent created successfully"
        except Exception as e:
            return None, f"Error creating agent: {e}"
    
    def update_agent(self, agent_id, user, data):
        from django.utils import timezone
        try:
            agent = Agent.objects.select_related("elevenlabs_voice").get(id=agent_id, owner=user)

            update_fields = []

            if data.agent_name is not None:
                agent.agent_name = data.agent_name
                update_fields.append("agent_name")

            if data.system_prompt is not None:
                agent.system_prompt = data.system_prompt
                update_fields.append("system_prompt")

            if data.language is not None:
                agent.language = data.language
                update_fields.append("language")

            if data.is_draft is not None:
                if data.is_draft and agent.status in ("live", "error"):
                    agent.status = "draft"
                    update_fields.append("status")
                elif not data.is_draft and agent.status == "draft":
                    agent.status = "live"
                    update_fields.append("status")

            if data.elevenlabs_voice_id is not None:
                if data.elevenlabs_voice_id:
                    voice, _ = ElevenLabsVoiceMechanism().get_elevenVoice_by_voice_id(data.elevenlabs_voice_id)
                    if voice:
                        agent.elevenlabs_voice = voice
                        update_fields.append("elevenlabs_voice")
                else:
                    agent.elevenlabs_voice = None
                    update_fields.append("elevenlabs_voice")

            if update_fields:
                update_fields.append("updated_at")
                agent.save(update_fields=update_fields)

            if data.user_tools is not None:
                AgentUserTool.objects.filter(agent=agent).delete()
                for ut_id in data.user_tools:
                    try:
                        ut = UserTool.objects.get(id=ut_id, owner=user)
                        AgentUserTool.objects.create(agent=agent, user_tool=ut)
                    except UserTool.DoesNotExist:
                        pass

            if data.phone_number_id is not None:
                current_phone = getattr(agent, "phone_number", None)
                if current_phone and str(current_phone.id) == data.phone_number_id:
                    pass  # same phone, no change
                else:
                    if current_phone:
                        current_phone.agent      = None
                        current_phone.status     = "active"
                        current_phone.assigned_at = None
                        current_phone.save(update_fields=["agent", "status", "assigned_at"])
                    if data.phone_number_id:
                        phone, _ = PhoneNumberMechanism().get_phone_number_by_id(data.phone_number_id)
                        if phone:
                            phone.agent      = agent
                            phone.status     = "active"
                            phone.assigned_at = timezone.now()
                            phone.save(update_fields=["agent", "status", "assigned_at"])

            agent = (
                Agent.objects
                .select_related("owner", "owner__tenant", "elevenlabs_voice")
                .prefetch_related("tools", "user_tools", "phone_number")
                .get(id=agent_id, owner=user)
            )
            return agent, "Agent updated successfully"
        except Agent.DoesNotExist:
            return None, "Agent not found"
        except Exception as e:
            return None, f"Error updating agent: {e}"

    def delete_agent(self, agent_id, user):
        try:
            agent = Agent.objects.get(id=agent_id, owner=user)
            agent.delete()
            return agent, "Agent deleted successfully"
        except Agent.DoesNotExist:
            return None, "Agent not found"
        except Exception as e:
            return None, f"Error deleting agent: {e}"

    def get_all_agents(self, user, search=None):
        try:
            qs = (
                Agent.objects
                .filter(owner=user)
                .select_related("owner", "owner__tenant")
                .prefetch_related("tools", "user_tools", "phone_number")
                .order_by("-created_at")
            )
            if search:
                qs = qs.filter(agent_name__icontains=search)
            return qs, "Agents fetched successfully"
        except Exception as e:
            return None, f"Error fetching agents: {e}"

    def get_agent_by_id(self, agent_id, user):
        try:
            agent = (
                Agent.objects
                .select_related("owner", "owner__tenant")
                .prefetch_related("tools", "user_tools", "phone_number")
                .get(id=agent_id, owner=user)
            )
            return agent, "Agent fetched successfully"
        except Agent.DoesNotExist:
            return None, "Agent not found"
        except Exception as e:
            return None, f"Error fetching agent: {e}"
        


class UserToolMechanism:
    def get_all_user_tools(self, user, search=None):
        try:
            qs = UserTool.objects.filter(owner=user).order_by("-created_at")
            if search:
                qs = qs.filter(name__icontains=search)
            return qs, "Tools fetched successfully"
        except Exception as e:
            return None, f"Error fetching tools: {e}"

    def get_tool_by_id(self, tool_id, user):
        try:
            tool = UserTool.objects.get(id=tool_id, owner=user)
            return tool, "Tool fetched successfully"
        except UserTool.DoesNotExist:
            return None, "Tool not found"
        except Exception as e:
            return None, f"Error fetching tool: {e}"

    def create_tool(self, user, data):
        try:
            tool = UserTool.objects.create(
                owner=user,
                name=data.name,
                description=data.description or "",
                tool_type=data.tool_type or "webhook",
                webhook_url=data.webhook_url or "",
                parameters=data.parameters or {},
            )
            return tool, "Tool created successfully"
        except Exception as e:
            return None, f"Error creating tool: {e}"

    def update_tool(self, tool_id, user, data):
        try:
            tool = UserTool.objects.get(id=tool_id, owner=user)
            update_fields = []

            if data.name is not None:
                tool.name = data.name
                update_fields.append("name")
            if data.description is not None:
                tool.description = data.description
                update_fields.append("description")
            if data.tool_type is not None:
                tool.tool_type = data.tool_type
                update_fields.append("tool_type")
            if data.webhook_url is not None:
                tool.webhook_url = data.webhook_url
                update_fields.append("webhook_url")
            if data.parameters is not None:
                tool.parameters = data.parameters
                update_fields.append("parameters")
            if data.is_active is not None:
                tool.is_active = data.is_active
                update_fields.append("is_active")

            if update_fields:
                update_fields.append("updated_at")
                tool.save(update_fields=update_fields)

            return tool, "Tool updated successfully"
        except UserTool.DoesNotExist:
            return None, "Tool not found"
        except Exception as e:
            return None, f"Error updating tool: {e}"

    def delete_tool(self, tool_id, user):
        try:
            tool = UserTool.objects.get(id=tool_id, owner=user)
            tool.delete()
            return True, "Tool deleted successfully"
        except UserTool.DoesNotExist:
            return None, "Tool not found"
        except Exception as e:
            return None, f"Error deleting tool: {e}"


class PhoneNumberMechanism:
    def get_all_numbers(self):
        try:
            numbers = PhoneNumber.objects.select_related("agent").order_by("-created_at")
            return numbers, "Phone numbers fetched successfully"
        except Exception as e:
            return None, f"Error fetching phone numbers: {e}"

    def get_available_numbers(self):
        try:
            numbers = PhoneNumber.objects.filter(agent=None, status="active").order_by("-created_at")
            return numbers, "Available phone numbers fetched successfully"
        except Exception as e:
            return None, f"Error fetching available numbers: {e}"

    def get_phone_number_by_id(self, phone_id):
        try:
            phone = PhoneNumber.objects.get(id=phone_id, agent=None)
            return phone, "Phone number fetched successfully"
        except PhoneNumber.DoesNotExist:
            return None, "Phone number not found or already assigned"
        except Exception as e:
            return None, f"Error fetching phone number: {e}"