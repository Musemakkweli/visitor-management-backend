
from typing import Literal
from datetime import date, time, datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ConfigDict,
    model_validator,
)


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
            raise ValueError(
                "Employee number is required for employee registration."
            )

        if self.account_type == "visitor" and self.employee_number:
            raise ValueError(
                "Visitors must not provide an employee number."
            )

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


# Visitor appointment request
class AppointmentCreate(BaseModel):
    destination: str = Field(min_length=2, max_length=150)
    purpose: str = Field(min_length=5)
    visit_date: date
    visit_time: time


# Appointment information returned by the backend
class AppointmentResponse(BaseModel):
    id: int
    request_number: str
    visitor_id: int
    destination: str
    purpose: str
    visit_date: date
    visit_time: time
    status: str
    response_message: str | None = None
    reviewed_at: datetime | None = None
    reviewed_by: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Dashboard statistics
class DashboardStatistics(BaseModel):
    total_requests: int
    pending: int
    approved: int
    rejected: int


# Visitor dashboard response
class DashboardResponse(BaseModel):
    statistics: DashboardStatistics
    recent_requests: list[AppointmentResponse]


# =====================================================
# VISITOR PROFILE SCHEMAS
# =====================================================

# Information submitted when updating a visitor profile
class VisitorProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    organization: str | None = Field(default=None, max_length=150)
    address: str | None = Field(default=None, max_length=255)


# Visitor profile information returned by the backend
class VisitorProfileResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    organization: str | None
    address: str | None

    model_config = ConfigDict(from_attributes=True)
# =====================================================
# APPOINTMENT REVIEW SCHEMAS
# =====================================================

class AppointmentReview(BaseModel):
    status: Literal["approved", "rejected"]
    response_message: str = Field(min_length=2, max_length=1000)
[{
	"resource": "/h:/visitor-management/backend/app/schemas.py",
	"owner": "Pylance",
	"severity": 8,
	"message": "Expected indented block",
	"source": "Pylance",
	"startLineNumber": 130,
	"startColumn": 1,
	"endLineNumber": 130,
	"endColumn": 6,
	"modelVersionId": 12,
	"origin": "extHost1"
},{
	"resource": "/h:/visitor-management/backend/app/schemas.py",
	"owner": "Pylance",
	"code": {
		"value": "reportMissingImports",
		"target": {
			"$mid": 1,
			"path": "/microsoft/pylance-release/blob/main/docs/diagnostics/reportMissingImports.md",
			"scheme": "https",
			"authority": "github.com"
		}
	},
	"severity": 4,
	"message": "Import \"pydantic\" could not be resolved",
	"source": "Pylance",
	"startLineNumber": 5,
	"startColumn": 6,
	"endLineNumber": 5,
	"endColumn": 14,
	"modelVersionId": 12,
	"origin": "extHost1"
}]
# =====================================================
# VISITOR CHECK-IN / CHECK-OUT SCHEMAS
# =====================================================

class VisitCheckIn(BaseModel):
    visitor_id: int
    appointment_id: int | None = None
    destination: str = Field(min_length=2, max_length=150)
    purpose: str = Field(min_length=5)


class VisitResponse(BaseModel):
    id: int
    visitor_id: int
    appointment_id: int | None
    destination: str
    purpose: str
    check_in_time: datetime
    check_out_time: datetime | None
    checked_in_by: int
    checked_out_by: int | None
    status: str

    model_config = ConfigDict(from_attributes=True)
class ReceptionistVisitorCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = None
    organization: str | None = None
    address: str | None = None
    password: str = Field(min_length=8)