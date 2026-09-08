from typing import Optional
from pydantic import BaseModel, field_validator


class UpdateAgentSchema(BaseModel):
    agent_name:          Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    system_prompt:       Optional[str] = None
    language:            Optional[str] = None
    phone_number:        Optional[str] = None

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
        if v is not None:
            v = v.strip()
            if len(v) > 20:
                raise ValueError("Language code must be 20 characters or less")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) > 20:
                raise ValueError("Phone number must be 20 characters or less")
        return v


class CreateAgentSchema(BaseModel):
    agent_name:          str
    elevenlabs_voice_id: Optional[str] = None
    system_prompt:       Optional[str] = None
    language:            Optional[str] = "en-US"
    phone_number:        Optional[str] = ""

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
        if v is None:
            return "en-US"
        v = v.strip() or "en-US"
        if len(v) > 20:
            raise ValueError("Language code must be 20 characters or less")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return ""
        v = v.strip()
        if len(v) > 20:
            raise ValueError("Phone number must be 20 characters or less")
        return v
