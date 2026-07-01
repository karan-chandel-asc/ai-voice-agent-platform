from typing import Optional, Any
from pydantic import BaseModel, field_validator, model_validator


class UpdateAgentSchema(BaseModel):
    agent_name:          Optional[str]       = None
    elevenlabs_voice_id: Optional[str]       = None
    system_prompt:       Optional[str]       = None
    language:            Optional[str]       = None
    user_tools:          Optional[list[str]] = None
    phone_number_id:     Optional[str]       = None
    is_draft:            Optional[bool]      = None

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Agent name cannot be empty")
            if len(v) > 100:
                raise ValueError("Agent name must be 100 characters or less")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        if v and len(v) > 10:
            raise ValueError("Language code must be 10 characters or less")
        return v


class CreateAgentSchema(BaseModel):
    agent_name:          str
    elevenlabs_voice_id: Optional[str]       = None
    system_prompt:       Optional[str]       = None
    language:            Optional[str]       = "en"
    user_tools:          Optional[list[str]] = []
    phone_number_id:     Optional[str]       = None
    is_draft:            Optional[bool]      = False

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Agent name is required")
        if len(v) > 100:
            raise ValueError("Agent name must be 100 characters or less")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        if v and len(v) > 10:
            raise ValueError("Language code must be 10 characters or less")
        return v


# ── UserTool schemas ───────────────────────────────────────────────────────────

class CreateUserToolSchema(BaseModel):
    name:        str
    description: Optional[str] = ""
    tool_type:   Optional[str] = "webhook"
    webhook_url: Optional[str] = ""
    parameters:  Optional[Any] = {}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Tool name is required")
        if len(v) > 100:
            raise ValueError("Tool name must be 100 characters or less")
        return v

    @field_validator("tool_type")
    @classmethod
    def validate_tool_type(cls, v):
        if v not in ("webhook", "builtin"):
            raise ValueError("tool_type must be 'webhook' or 'builtin'")
        return v

    @model_validator(mode="after")
    def webhook_requires_url(self):
        if self.tool_type == "webhook" and not self.webhook_url:
            raise ValueError("webhook_url is required for webhook tools")
        return self


class UpdateUserToolSchema(BaseModel):
    name:        Optional[str]  = None
    description: Optional[str]  = None
    tool_type:   Optional[str]  = None
    webhook_url: Optional[str]  = None
    parameters:  Optional[Any]  = None
    is_active:   Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Tool name cannot be empty")
            if len(v) > 100:
                raise ValueError("Tool name must be 100 characters or less")
        return v

    @field_validator("tool_type")
    @classmethod
    def validate_tool_type(cls, v):
        if v is not None and v not in ("webhook", "builtin"):
            raise ValueError("tool_type must be 'webhook' or 'builtin'")
        return v
