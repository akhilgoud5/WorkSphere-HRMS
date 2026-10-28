from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from typing import Literal

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = "EMPLOYEE"

class LoginIn(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class EmployeeIn(BaseModel):
    user_id: int | None = None
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr | None = None
    designation: str = ""
    department: str = ""
    joining_date: date | None = None
    salary: float = Field(default=0, ge=0)
    status: str = "ACTIVE"

class EmployeeOut(BaseModel):
    id: int
    user_id: int | None = None
    full_name: str
    email: str | None = None
    designation: str | None = None
    department: str | None = None
    joining_date: date | None = None
    salary: float = 0
    status: str = "ACTIVE"

    class Config:
        from_attributes = True

class LeaveIn(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(min_length=1, max_length=500)
    policy_id: int | None = None

class LeaveOut(BaseModel):
    id: int
    employee_id: int
    start_date: date
    end_date: date
    reason: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LeaveBalanceCreate(BaseModel):
    employee_id: int
    policy_id: int
    year: int
    allocated_days: int = Field(ge=0)


class LeaveBalanceOut(BaseModel):
    id: int
    employee_id: int
    policy_id: int
    year: int
    allocated_days: int
    used_days: int

    model_config = ConfigDict(from_attributes=True)

class OnboardingCreate(BaseModel):
    employee_id: int = Field(gt=0)
    task_name: str = Field(min_length=1, max_length=200)
    due_date: date | None = None


class OnboardingStatusUpdate(BaseModel):
    status: Literal["PENDING", "COMPLETED"]


class OnboardingOut(BaseModel):
    id: int
    employee_id: int
    task_name: str
    status: str
    due_date: date | None = None

    class Config:
        from_attributes = True   



class FeedbackCreate(BaseModel):
    message: str = Field(..., min_length=3, max_length=2000)
    rating: int = Field(..., ge=1, le=5)


class FeedbackOut(BaseModel):
    id: int
    employee_id: int
    message: str
    rating: int
    created_at : datetime

    class Config:
        from_attributes = True        

class ProfileUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=150)
    designation: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)        