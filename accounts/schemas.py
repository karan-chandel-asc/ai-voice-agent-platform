import re
from pydantic import BaseModel, field_validator


class ForgotPasswordSchema(BaseModel):
    """Validate forgot-password request body.

    Requires a well-formed email address.
    Used by ForgotPasswordView before token creation.
    """

    email: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Reject strings that are not valid emails."""
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email address')
        return v


class ResetPasswordSchema(BaseModel):
    """Validate reset-password request body.

    Requires uid, token, and a new password.
    Enforces a minimum password length of 8.
    """

    uid: str
    token: str
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Ensure password meets the minimum length."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class LoginViewSchema(BaseModel):
    """Validate login request body.

    Requires email and a non-empty password.
    Used by LoginAPIView before authentication.
    """

    email: str
    password: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Reject strings that are not valid emails."""
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email address')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Reject blank or whitespace-only passwords."""
        if not v.strip():
            raise ValueError('Password is required')
        return v
