from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, Float, ForeignKey
from .database import Base
from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="EMPLOYEE")
    created_at = Column(DateTime, default=datetime.utcnow)

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=True)
    designation = Column(String(100), default="")
    department = Column(String(100), default="")
    joining_date = Column(Date, nullable=True)
    salary = Column(Float, default=0)
    status = Column(String(20), default="ACTIVE")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False
    )
    attendance_date = Column(Date, default=date.today, nullable=False)
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    status = Column(String(20), default="PRESENT")
    created_at = Column(DateTime, default=datetime.utcnow)


 
class Leave(Base):
    __tablename__ = "leaves"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False
    )
    policy_id = Column(
        Integer,
        ForeignKey("leave_policies.id"),
        nullable=True
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    

class Payroll(Base):
    __tablename__ = "payrolls"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False
    )

    month = Column(String(20), nullable=False)
    basic_salary = Column(Float, nullable=False)
    allowances = Column(Float, default=0.0, nullable=False)
    deductions = Column(Float, default=0.0, nullable=False)
    net_salary = Column(Float, nullable=False)

    payment_status = Column(
        String(20),
        default="PENDING",
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class LeavePolicy(Base):
    __tablename__ = "leave_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    annual_days = Column(Integer, nullable=False, default=12)
    description = Column(String(255), default="")
    is_active = Column(Boolean, default=True)


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False
    )
    policy_id = Column(
        Integer,
        ForeignKey("leave_policies.id"),
        nullable=False
    )
    year = Column(Integer, nullable=False)
    allocated_days = Column(Integer, nullable=False, default=12)
    used_days = Column(Integer, nullable=False, default=0) 