
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    account_type: Literal["visitor", "employee"] = "visitor"
    employee_number: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_account_type(self):
        if self.account_type == "employee" and not self.employee_number:
            raise ValueError("Employee number is required for employee registration.")

        if self.account_type == "visitor" and self.employee_number:
            raise ValueError("Visitors must not provide an employee number.")

        return self


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
