from django.db.models import Q
from .models import Agent, ElevenLabsVoice, AgentUserTool, UserTool


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
        try:
            agent = Agent.objects.create(
                owner=user,
                agent_name=data.agent_name,
                system_prompt=data.system_prompt or "",
                language=data.language or "en",
                phone_number=(data.phone_number or "").strip(),
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

            return agent, "Agent created successfully"
        except Exception as e:
            return None, f"Error creating agent: {e}"

    def update_agent(self, agent_id, user, data):
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

            if data.phone_number is not None:
                agent.phone_number = data.phone_number.strip()
                update_fields.append("phone_number")

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
                .prefetch_related("user_tools__user_tool")
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
                .prefetch_related("user_tools__user_tool")
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
            deleted, _ = Agent.objects.filter(owner=user).delete()
            return deleted, "All agents deleted successfully"
        except Exception as e:
            return None, f"Error deleting agents: {e}"


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
                tool_type=data.tool_type or "builtin",
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
