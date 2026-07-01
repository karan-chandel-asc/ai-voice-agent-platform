from  core.logger import logger
from pydantic import ValidationError
from pydantic import BaseModel, field_validator


from pydantic import BaseModel, Field, field_validator
import re

E164_REGEX = re.compile(r"^\+[1-9]\d{1,14}$")


class TwilioInboundForm(BaseModel):
    call_sid: str = Field(alias="CallSid")
    from_number: str = Field(alias="From")
    to_number: str = Field(alias="To")

    @field_validator("call_sid")
    @classmethod
    def validate_call_sid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("CallSid is required")
        return v

    @field_validator("from_number", "to_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        v = v.strip()

        if not E164_REGEX.match(v):
            raise ValueError(
                "Phone number must be in E.164 format (e.g. +1234567890)"
            )

        return v