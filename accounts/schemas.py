import re
from pydantic import BaseModel, field_validator, model_validator


# schema for sighnup
class SignupViewSchema(BaseModel):
    first_name: str
    last_name: str
    business_name: str
    work_email: str
    password: str

    @field_validator('first_name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('First Name is required')
        if len(v) > 50:
            raise ValueError('Max length is 50 characters')
        return v
    
    @field_validator('last_name')
    @classmethod
    def validate_last_name(cls, v):
        if not v.strip():
            raise ValueError('Last Name is required')
        if len(v) > 50:
            raise ValueError('Max length is 50 characters')
        return v

    @field_validator('business_name')
    @classmethod
    def validate_business_name(cls, v):
        if not v.strip():
            raise ValueError('This field is required')
        if len(v) > 255:
            raise ValueError('Max length is 255 characters')
        return v

    @field_validator('work_email')
    @classmethod
    def validate_email(cls, v):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email address')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class ForgotPasswordSchema(BaseModel):
    email: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email address')
        return v


class ResetPasswordSchema(BaseModel):
    uid: str
    token: str
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class LoginViewSchema(BaseModel):
    email: str
    password: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email address')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not v.strip():
            raise ValueError('Password is required')
        return v
