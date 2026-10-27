from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .database import Base, engine, get_db
from .security import hash_password, verify_password, create_access_token
from .dependencies import current_user, allow_roles
from datetime import datetime, date
from fastapi.security import OAuth2PasswordRequestForm
from .models import Payroll
from . import models, schemas
from .shift_routes import router as shift_router
from app.schemas import LeaveIn
from datetime import date, datetime
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import LeaveBalanceCreate
from app.routers import documents
from app.routers import performance
from app import models
from app.routers import notifications
from app.models import User, Employee, Leave
from app.routers import analytics
from datetime import datetime, timedelta
from app.models import Notification

app = FastAPI(title="WorkSphere HRMS API", version="1.0.0",
              description="Starter API for WorkSphere HR Management System")
Base.metadata.create_all(bind=engine)

from sqlalchemy import inspect, text

# Add the missing shift_id column to the existing attendance table
inspector = inspect(engine)

if "attendance" in inspector.get_table_names():
    columns = [
        column["name"]
        for column in inspector.get_columns("attendance")
    ]

    if "shift_id" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE attendance "
                    "ADD COLUMN shift_id INTEGER REFERENCES shifts(id)"
                )
            )
        print("Migration successful: shift_id added to attendance.")

app.include_router(shift_router)
app.include_router(documents.router)
app.include_router(performance.router)
app.include_router(notifications.router)
app.include_router(analytics.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "WorkSphere HRMS API is running", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(data: schemas.RegisterIn, db: Session = Depends(get_db)):
    role = data.role.upper()
    # Public registration must not let a new user grant themselves HR or ADMIN access.
    if role != "EMPLOYEE":
        raise HTTPException(status_code=400, detail="Public registration only supports EMPLOYEE role")
    if db.query(models.User).filter(
        (models.User.username == data.username) | (models.User.email == data.email)
    ).first():
        raise HTTPException(status_code=409, detail="Username or email already exists")
    user = models.User(username=data.username, email=data.email,
                       hashed_password=hash_password(data.password), role="EMPLOYEE")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user



@app.post("/auth/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(
        models.User.username == form_data.username
    ).first()

    if not user or not verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    token = create_access_token(
    subject=str(user.id),
    role=user.role,
)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        },
    }



@app.post("/auth/token")
def get_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(
        models.User.username == form_data.username
    ).first()

    if not user or not verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.get("/auth/me", response_model=schemas.UserOut)
def me(user=Depends(current_user)):
    return user


@app.post(
    "/employees",
    response_model=schemas.EmployeeOut,
    status_code=201
)
def create_employee(
    data: schemas.EmployeeIn,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    employee_data = data.model_dump()

    # Check whether this user is already linked
    user_id = employee_data.get("user_id")

    if user_id is not None:
        existing = (
            db.query(models.Employee)
            .filter(models.Employee.user_id == user_id)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="This user is already linked to an employee. Use user_id: null for an unlinked employee."
            )

    try:
        print("EMPLOYEE EMAIL RECEIVED:", data.email)
        employee_data = data.model_dump()
        print("EMPLOYEE DATA RECEIVED:", employee_data)
        employee = models.Employee(**employee_data)
        db.add(employee)
        db.commit()
        db.refresh(employee)

    except Exception as exc:
        db.rollback()
        print("CREATE EMPLOYEE ERROR:", exc)
        raise HTTPException(
            status_code=400,
            detail="Employee creation failed. Check the backend terminal."
        )

    return employee

    
@app.get("/employees", response_model=list[schemas.EmployeeOut])
def list_employees(
    search: str = "",
    department: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    query = db.query(models.Employee)

    if search:
        query = query.filter(
            models.Employee.full_name.ilike(f"%{search}%")
        )

    if department:
        query = query.filter(
            models.Employee.department.ilike(f"%{department}%")
        )

    if status:
        query = query.filter(
            models.Employee.status.ilike(f"%{status}%")
        )

    employees = query.order_by(
        models.Employee.id.desc()
    ).all()

    results = []

    for employee in employees:
        employee_data = (
            schemas.EmployeeOut.model_validate(employee).model_dump()
        )

        email = employee.email

        if not email and employee.user_id is not None:
            linked_user = db.query(models.User).filter(
                models.User.id == employee.user_id
            ).first()

            if linked_user:
                email = linked_user.email

        employee_data["email"] = email
        results.append(employee_data)

    return results


@app.put("/employees/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(employee_id: int, data: schemas.EmployeeIn, db: Session = Depends(get_db),
                    user=Depends(allow_roles("HR", "ADMIN"))):
    employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    for key, value in data.model_dump().items():
        setattr(employee, key, value)
    db.commit()
    db.refresh(employee)
    return employee

@app.delete("/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: int, db: Session = Depends(get_db),
                    user=Depends(allow_roles("HR", "ADMIN"))):
    employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(employee)
    db.commit()
    return None

    
@app.get("/dashboard/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    total = db.query(models.Employee).count()

    active = db.query(models.Employee).filter(
        models.Employee.status == "ACTIVE"
    ).count()

    inactive = db.query(models.Employee).filter(
        models.Employee.status == "INACTIVE"
    ).count()

    departments = db.query(
        models.Employee.department
    ).filter(
        models.Employee.department.isnot(None),
        models.Employee.department != ""
    ).distinct().count()

    present_today = db.query(models.Attendance).filter(
        models.Attendance.attendance_date == date.today(),
        models.Attendance.status == "PRESENT"
    ).count()

    pending_leaves = db.query(models.Leave).filter(
        models.Leave.status == "PENDING"
    ).count()

    return {
        "total_employees": total,
        "active_employees": active,
        "inactive_employees": inactive,
        "departments": departments,
        "present_today": present_today,
        "pending_leaves": pending_leaves
    }


@app.get("/analytics/attendance")
def attendance_analytics(
    report_date: date = None,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    from sqlalchemy import func

    selected_date = report_date or date.today()

    total_records = db.query(models.Attendance).filter(
        models.Attendance.attendance_date == selected_date
    ).count()

    present = db.query(models.Attendance).filter(
        models.Attendance.attendance_date == selected_date,
        models.Attendance.status == "PRESENT"
    ).count()

    absent = db.query(models.Attendance).filter(
        models.Attendance.attendance_date == selected_date,
        models.Attendance.status == "ABSENT"
    ).count()

    late = db.query(models.Attendance).filter(
        models.Attendance.attendance_date == selected_date,
        func.upper(models.Attendance.status).like("%LATE%")
    ).count()

    return {
        "report_date": selected_date.isoformat(),
        "total_attendance_records": total_records,
        "present": present,
        "absent": absent,
        "late": late
    }

@app.get("/analytics/leaves")
def leave_analytics(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    total = db.query(models.Leave).count()

    pending = db.query(models.Leave).filter(
        models.Leave.status == "PENDING"
    ).count()

    approved = db.query(models.Leave).filter(
        models.Leave.status == "APPROVED"
    ).count()

    rejected = db.query(models.Leave).filter(
        models.Leave.status == "REJECTED"
    ).count()

    return {
        "total_leave_requests": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected
    }

@app.post("/attendance/check-in")
def check_in(
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    now = datetime.now()
    today = now.date()

    # 1. Find employee profile
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    # 2. Find today's attendance record
    record = db.query(models.Attendance).filter(
        models.Attendance.employee_id == employee.id,
        models.Attendance.attendance_date == today
    ).first()

    if record and record.check_in:
        raise HTTPException(
            status_code=400,
            detail="Already checked in today"
        )

    # 3. Find the employee's assigned shift
    assignment = db.query(models.EmployeeShift).filter(
        models.EmployeeShift.employee_id == employee.id
    ).first()

    shift = None

    if assignment:
        shift = db.query(models.Shift).filter(
            models.Shift.id == assignment.shift_id
        ).first()

    # 4. Determine attendance status
    status = "PRESENT"

    if shift:
         shift_start = shift.start_time

    if isinstance(shift_start, str):
        shift_start = datetime.strptime(
            shift_start, "%H:%M:%S"
        ).time()

    shift_start_datetime = datetime.combine(
        today, shift_start
    )
    grace_period = timedelta(minutes=5)

    if now > shift_start_datetime + grace_period:
        status = "LATE"

    # 5. Create or update attendance
    if not record:
        record = models.Attendance(
            employee_id=employee.id,
            attendance_date=today,
            check_in=now,
            status=status
        )

        if hasattr(record, "shift_id") and shift:
            record.shift_id = shift.id

        db.add(record)

    else:
        record.check_in = now
        record.status = status

        if hasattr(record, "shift_id") and shift:
            record.shift_id = shift.id

    db.commit()
    db.refresh(record)

    return record


@app.post("/attendance/check-out")
def check_out(
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    now = datetime.now()
    today = now.date()

    # 1. Find employee profile
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    # 2. Find today's attendance
    record = db.query(models.Attendance).filter(
        models.Attendance.employee_id == employee.id,
        models.Attendance.attendance_date == today
    ).first()

    if not record or not record.check_in:
        raise HTTPException(
            status_code=400,
            detail="Please check in first"
        )

    if record.check_out:
        raise HTTPException(
            status_code=400,
            detail="Already checked out today"
        )

    # 3. Find assigned shift
    assignment = db.query(models.EmployeeShift).filter(
        models.EmployeeShift.employee_id == employee.id
    ).first()

    shift = None

    if assignment:
        shift = db.query(models.Shift).filter(
            models.Shift.id == assignment.shift_id
        ).first()

    # 4. Record check-out
    record.check_out = now

    # Preserve LATE status if the employee checked in late.
    if shift and record.status != "LATE":
        shift_end = shift.end_time

        if isinstance(shift_end, str):
            shift_end = datetime.strptime(
                shift_end, "%H:%M:%S"
            ).time()

        if now.time() < shift_end:
            record.status = "EARLY_CHECKOUT"

    db.commit()
    db.refresh(record)

    return record

@app.get("/attendance")
def list_attendance(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    return db.query(models.Attendance).all()

@app.get("/attendance/me")
def my_attendance(
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    return db.query(models.Attendance).filter(
        models.Attendance.employee_id == employee.id
    ).order_by(
        models.Attendance.attendance_date.desc()
    ).all()

@app.get("/attendance/summary")
def attendance_summary(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    total_records = db.query(models.Attendance).count()

    present_days = db.query(models.Attendance).filter(
        models.Attendance.status == "PRESENT"
    ).count()

    absent_days = db.query(models.Attendance).filter(
        models.Attendance.status == "ABSENT"
    ).count()

    return {
        "total_attendance_records": total_records,
        "present_days": present_days,
        "absent_days": absent_days
    }


@app.post("/leaves", status_code=201)
def apply_leave(
    leave_data: LeaveIn,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    if leave_data.start_date > leave_data.end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date cannot be after end date"
        )

    # Validate the leave policy if provided
    if leave_data.policy_id is not None:
        policy = db.query(models.LeavePolicy).filter(
            models.LeavePolicy.id == leave_data.policy_id,
            models.LeavePolicy.is_active == True
        ).first()

        if not policy:
            raise HTTPException(
                status_code=404,
                detail="Active leave policy not found"
            )

    leave = models.Leave(
        employee_id=employee.id,
        policy_id=leave_data.policy_id,
        start_date=leave_data.start_date,
        end_date=leave_data.end_date,
        reason=leave_data.reason,
        status="PENDING"
    )

    db.add(leave)
    db.commit()
    db.refresh(leave)

    return leave


@app.get("/leaves/me")
def my_leaves(
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    return db.query(models.Leave).filter(
        models.Leave.employee_id == employee.id
    ).order_by(
        models.Leave.created_at.desc()
    ).all()


@app.put("/leaves/{leave_id}/approve")
def approve_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    # 1. Find the leave request
    leave = db.query(models.Leave).filter(
        models.Leave.id == leave_id
    ).first()

    if not leave:
        raise HTTPException(
            status_code=404,
            detail="Leave request not found"
        )

    # 2. Check leave status
    if leave.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Leave request has already been processed"
        )

    # 3. Validate leave dates
    if leave.end_date < leave.start_date:
        raise HTTPException(
            status_code=400,
            detail="End date cannot be before start date"
        )

    # 4. A policy must be selected before deducting leave
    if leave.policy_id is None:
        raise HTTPException(
            status_code=400,
            detail="This leave request has no leave policy assigned"
        )

    # 5. Calculate requested days (calendar days, including both dates)
    requested_days = (
        leave.end_date - leave.start_date
    ).days + 1

    # 6. Find the matching yearly leave balance
    leave_year = leave.start_date.year

    balance = db.query(models.LeaveBalance).filter(
        models.LeaveBalance.employee_id == leave.employee_id,
        models.LeaveBalance.policy_id == leave.policy_id,
        models.LeaveBalance.year == leave_year
    ).first()

    if not balance:
        raise HTTPException(
            status_code=404,
            detail="Leave balance not found for this employee, policy, and year"
        )

    # 7. Check remaining days
    remaining_days = balance.allocated_days - balance.used_days

    if requested_days > remaining_days:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient leave balance. Remaining days: {remaining_days}"
        )

        # 8. Update balance and approve the request
    try:
        balance.used_days += requested_days
        leave.status = "APPROVED"
        db.commit()
        db.refresh(leave)
        db.refresh(balance)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to approve leave and update balance"
        )

    # 9. Notify the employee
    employee = db.query(models.Employee).filter(
        models.Employee.id == leave.employee_id
    ).first()

    if employee and employee.user_id:
        try:
            notification = models.Notification(
                user_id=employee.user_id,
                title="Leave Approved",
                message=(
                    f"Your leave request from {leave.start_date} "
                    f"to {leave.end_date} has been approved."
                ),
                is_read=False,
                created_at=datetime.utcnow()
            )

            db.add(notification)
            db.commit()

        except Exception:
            db.rollback()
            print("Warning: Leave approved, but notification failed.")

    return {
        "message": "Leave approved successfully",
        "leave": leave,
        "leave_days_deducted": requested_days,
        "remaining_days": balance.allocated_days - balance.used_days
    }


@app.put("/leaves/{leave_id}/reject")
def reject_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    leave = db.query(models.Leave).filter(
        models.Leave.id == leave_id
    ).first()

    if not leave:
        raise HTTPException(
            status_code=404,
            detail="Leave request not found"
        )

    if leave.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Leave request has already been processed"
        )

    leave.status = "REJECTED"
    db.commit()
    db.refresh(leave)

    # Automatically notify the employee
    employee = db.query(models.Employee).filter(
        models.Employee.id == leave.employee_id
    ).first()

    if employee and employee.user_id:
        try:
            notification = models.Notification(
                user_id=employee.user_id,
                title="Leave Rejected",
                message=(
                    f"Your leave request from {leave.start_date} "
                    f"to {leave.end_date} has been rejected."
                ),
                is_read=False,
                created_at=datetime.utcnow()
            )

            db.add(notification)
            db.commit()

        except Exception:
            db.rollback()
            print("Warning: Leave rejected, but notification failed.")

    return {
        "message": "Leave rejected successfully",
        "leave": leave
    }


class LeaveCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str
    policy_id: int

@app.post("/leaves", status_code=201)
def apply_leave(
    leave_data: LeaveCreate,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    # 1. Validate leave dates
    if leave_data.end_date < leave_data.start_date:
        raise HTTPException(
            status_code=400,
            detail="End date cannot be before start date"
        )

    if leave_data.start_date < date.today():
        raise HTTPException(
            status_code=400,
            detail="Cannot apply for leave in the past"
        )

    # 2. Find employee
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    # 3. Find active leave policy
    policy = db.query(models.LeavePolicy).filter(
        models.LeavePolicy.id == leave_data.policy_id,
        models.LeavePolicy.is_active == True
    ).first()

    if not policy:
        raise HTTPException(
            status_code=404,
            detail="Active leave policy not found"
        )

    # 4. Calculate requested leave days, including start and end dates
    requested_days = (
        leave_data.end_date - leave_data.start_date
    ).days + 1

    # 5. Check for overlapping pending or approved leave
    overlapping_leave = db.query(models.Leave).filter(
        models.Leave.employee_id == employee.id,
        models.Leave.status.in_(["PENDING", "APPROVED"]),
        models.Leave.start_date <= leave_data.end_date,
        models.Leave.end_date >= leave_data.start_date
    ).first()

    if overlapping_leave:
        raise HTTPException(
            status_code=400,
            detail="You already have a pending or approved leave during these dates"
        )

    # 6. Find the employee's leave balance for the selected policy and year
    leave_year = leave_data.start_date.year

    balance = db.query(models.LeaveBalance).filter(
        models.LeaveBalance.employee_id == employee.id,
        models.LeaveBalance.policy_id == policy.id,
        models.LeaveBalance.year == leave_year
    ).first()

    if not balance:
        raise HTTPException(
            status_code=404,
            detail="Leave balance not found for this policy and year"
        )

    # 7. Check remaining leave days
    remaining_days = balance.allocated_days - balance.used_days

    if requested_days > remaining_days:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient leave balance. Remaining days: {remaining_days}"
        )

    # 8. Create leave request
    leave = models.Leave(
        employee_id=employee.id,
        policy_id=policy.id,
        start_date=leave_data.start_date,
        end_date=leave_data.end_date,
        reason=leave_data.reason,
        status="PENDING"
    )

    db.add(leave)
    db.commit()
    db.refresh(leave)

    return leave

@app.get("/leaves")
def get_my_leaves(
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    leaves = db.query(models.Leave).filter(
        models.Leave.employee_id == employee.id
    ).order_by(models.Leave.id.desc()).all()

    return leaves



@app.put("/leaves/{leave_id}/status")
def update_leave_status(
    leave_id: int,
    status: str,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    new_status = status.upper()

    if new_status not in ["APPROVED", "REJECTED"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be APPROVED or REJECTED"
        )

    leave = db.query(models.Leave).filter(
        models.Leave.id == leave_id
    ).first()

    if not leave:
        raise HTTPException(
            status_code=404,
            detail="Leave request not found"
        )

    # Do not deduct balance twice
    if leave.status == "APPROVED":
        if new_status == "REJECTED":
            raise HTTPException(
                status_code=400,
                detail="An approved leave cannot be rejected directly"
            )
        return leave

    if new_status == "APPROVED":
        leave_days = (leave.end_date - leave.start_date).days + 1

        balance = db.query(models.LeaveBalance).filter(
            models.LeaveBalance.employee_id == leave.employee_id,
            models.LeaveBalance.year == leave.start_date.year
        ).first()

        if not balance:
            raise HTTPException(
                status_code=404,
                detail="Leave balance not found for this employee and year"
            )

        remaining_days = balance.allocated_days - balance.used_days

        if remaining_days < leave_days:
            raise HTTPException(
                status_code=400,
                detail="Insufficient leave balance"
            )

        balance.used_days += leave_days

    leave.status = new_status
    db.commit()
    db.refresh(leave)

    return leave


@app.get("/attendance/my-summary")
def attendance_summary(
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    records = db.query(models.Attendance).filter(
        models.Attendance.employee_id == employee.id
    ).all()

    total_days = len(records)
    present_days = sum(
        1 for record in records
        if record.status == "PRESENT"
    )
    absent_days = sum(
        1 for record in records
        if record.status == "ABSENT"
    )

    return {
        "employee_id": employee.id,
        "total_attendance_records": total_days,
        "present_days": present_days,
        "absent_days": absent_days
    }




@app.post("/payroll", status_code=201)
def create_payroll(
    employee_id: int,
    month: str,
    basic_salary: float,
    allowances: float = 0,
    deductions: float = 0,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    if basic_salary < 0 or allowances < 0 or deductions < 0:
        raise HTTPException(
            status_code=400,
            detail="Salary, allowances, and deductions cannot be negative"
        )

    gross_salary = basic_salary + allowances

    if deductions > gross_salary:
        raise HTTPException(
            status_code=400,
            detail="Deductions cannot exceed gross salary"
        )

    payroll = models.Payroll(
        employee_id=employee_id,
        month=month,
        basic_salary=basic_salary,
        allowances=allowances,
        deductions=deductions,
        net_salary=gross_salary - deductions,
        payment_status="PENDING"
    )

    db.add(payroll)
    db.commit()
    db.refresh(payroll)

    # Notify the employee about payroll creation
    if employee.user_id:
        try:
            notification = models.Notification(
                user_id=employee.user_id,
                title="Payroll Generated",
                message=(
                    f"Your payroll for {month} has been generated. "
                    f"Net salary: {payroll.net_salary}."
                ),
                is_read=False,
                created_at=datetime.utcnow()
            )

            db.add(notification)
            db.commit()

        except Exception:
            db.rollback()
            print("Warning: Payroll created, but notification failed.")

    return payroll

  
@app.get("/payroll")
def get_payroll(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    return db.query(models.Payroll).all()


@app.get("/payroll/summary")
def payroll_summary(
    month: str,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    records = db.query(models.Payroll).filter(
        models.Payroll.month == month
    ).all()

    paid_records = [
        p for p in records if p.payment_status == "PAID"
    ]
    pending_records = [
        p for p in records if p.payment_status == "PENDING"
    ]

    return {
        "month": month,
        "total_payroll_records": len(records),
        "paid_payroll_records": len(paid_records),
        "pending_payroll_records": len(pending_records),
        "total_paid_salary": sum(p.net_salary for p in paid_records),
        "total_net_payroll_amount": sum(p.net_salary for p in records)
    }


@app.get("/payroll/{payroll_id}")
def get_payroll_by_id(
    payroll_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    payroll = db.query(models.Payroll).filter(
        models.Payroll.id == payroll_id
    ).first()

    if not payroll:
        raise HTTPException(
            status_code=404,
            detail="Payroll record not found"
        )

    return payroll


@app.put("/payroll/{payroll_id}/status")
def update_payroll_status(
    payroll_id: int,
    status: str,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    if status not in ["PAID", "PENDING"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be PAID or PENDING"
        )

    payroll = db.query(models.Payroll).filter(
        models.Payroll.id == payroll_id
    ).first()

    if payroll is None:
        raise HTTPException(
            status_code=404,
            detail="Payroll record not found"
        )

    payroll.payment_status = status
    db.commit()
    db.refresh(payroll)

    return payroll



@app.post("/auth/create-hr")
def create_hr_account(
    data: schemas.RegisterIn,
    db: Session = Depends(get_db),
    admin=Depends(allow_roles("ADMIN"))
):
    existing = db.query(models.User).filter(
        (models.User.username == data.username) |
        (models.User.email == data.email)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists"
        )

    hr_user = models.User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role="HR"
    )

    db.add(hr_user)
    db.commit()
    db.refresh(hr_user)

    return {
        "message": "HR account created successfully",
        "id": hr_user.id,
        "username": hr_user.username,
        "role": hr_user.role
    }


@app.get("/admin/analytics")
def admin_analytics(
    db: Session = Depends(get_db),
    admin=Depends(allow_roles("ADMIN"))
):
    total_users = db.query(models.User).count()
    total_employees = db.query(models.Employee).count()

    active_employees = db.query(models.Employee).filter(
        models.Employee.status == "ACTIVE"
    ).count()

    total_attendance = db.query(models.Attendance).count()

    total_leaves = db.query(models.Leave).count()
    pending_leaves = db.query(models.Leave).filter(
        models.Leave.status == "PENDING"
    ).count()

    approved_leaves = db.query(models.Leave).filter(
        models.Leave.status == "APPROVED"
    ).count()

    total_payroll = db.query(models.Payroll).count()

    paid_payroll = db.query(models.Payroll).filter(
        models.Payroll.payment_status == "PAID"
    ).count()

    pending_payroll = db.query(models.Payroll).filter(
        models.Payroll.payment_status == "PENDING"
    ).count()

    paid_amount = db.query(
        models.Payroll.net_salary
    ).filter(
        models.Payroll.payment_status == "PAID"
    ).all()

    total_paid_salary = sum(
        float(row[0] or 0) for row in paid_amount
    )

    total_net_payroll = db.query(
        models.Payroll.net_salary
    ).all()

    total_payroll_amount = sum(
        float(row[0] or 0) for row in total_net_payroll
    )

    return {
        "total_users": total_users,
        "total_employees": total_employees,
        "active_employees": active_employees,
        "total_attendance_records": total_attendance,
        "total_leave_requests": total_leaves,
        "pending_leave_requests": pending_leaves,
        "approved_leave_requests": approved_leaves,
        "total_payroll_records": total_payroll,
        "paid_payroll_records": paid_payroll,
        "pending_payroll_records": pending_payroll,
        "total_paid_salary": total_paid_salary,
        "total_net_payroll_amount": total_payroll_amount
    }



@app.get("/notifications")
def get_notifications(
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    print("Logged-in user ID:", user.id)
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user.id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )


@app.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == user.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )

    notification.is_read = True
    db.commit()
    db.refresh(notification)

    return {
        "message": "Notification marked as read",
        "notification": notification
    }

@app.post("/notifications")
def create_notification(
    user_id: int,
    title: str,
    message: str,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    notification = models.Notification(
        user_id=user_id,
        title=title,
        message=message
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


@app.post("/leaves", response_model=schemas.LeaveOut, status_code=201)
def apply_leave(
    data: schemas.LeaveIn,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    if data.end_date < data.start_date:
        raise HTTPException(
            status_code=400,
            detail="End date cannot be before start date",
        )

    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found. Ask HR to link your user account.",
        )

    leave = models.Leave(
        employee_id=employee.id,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
        status="PENDING",
    )

    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


@app.get("/leaves", response_model=list[schemas.LeaveOut])
def list_leaves(
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if user.role in ["ADMIN", "HR"]:
        return db.query(models.Leave).order_by(
            models.Leave.id.desc()
        ).all()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found. Ask HR to link your user account.",
        )

    return db.query(models.Leave).filter(
        models.Leave.employee_id == employee.id
    ).order_by(models.Leave.id.desc()).all()

@app.get("/leaves")
def list_leaves(
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    return (
        db.query(models.Leave)
        .order_by(models.Leave.id.desc())
        .all()
    )

@app.patch("/leaves/{leave_id}/status", response_model=schemas.LeaveOut)
def update_leave_status(
    leave_id: int,
    status: str,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN")),
):
    if status.upper() not in ["APPROVED", "REJECTED"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be APPROVED or REJECTED",
        )

    leave = db.query(models.Leave).filter(
        models.Leave.id == leave_id
    ).first()

    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if leave.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Only pending leave requests can be updated",
        )

    leave.status = status.upper()
    db.commit()
    db.refresh(leave)
    return leave

@app.patch("/leaves/{leave_id}/status")
def update_leave_status(
    leave_id: int,
    status: str,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    if status not in ["APPROVED", "REJECTED"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be APPROVED or REJECTED"
        )

    leave = db.query(models.Leave).filter(
        models.Leave.id == leave_id
    ).first()

    if not leave:
        raise HTTPException(
            status_code=404,
            detail="Leave request not found"
        )

    leave.status = status
    db.commit()
    db.refresh(leave)
    return leave 

class LeavePolicyCreate(BaseModel):
    name: str
    annual_days: int
    description: str = ""


@app.post("/leave-policies", status_code=201)
def create_leave_policy(
    policy_data: LeavePolicyCreate,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    if policy_data.annual_days <= 0:
        raise HTTPException(
            status_code=400,
            detail="Annual leave days must be greater than zero"
        )

    existing = db.query(models.LeavePolicy).filter(
        models.LeavePolicy.name == policy_data.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Leave policy already exists"
        )

    policy = models.LeavePolicy(
        name=policy_data.name,
        annual_days=policy_data.annual_days,
        description=policy_data.description
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return policy

class LeaveBalanceCreate(BaseModel):
    employee_id: int
    policy_id: int
    year: int
    allocated_days: int


@app.post("/leave-balances", status_code=201)
def create_leave_balance(
    balance_data: LeaveBalanceCreate,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    employee = db.query(models.Employee).filter(
        models.Employee.id == balance_data.employee_id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    policy = db.query(models.LeavePolicy).filter(
        models.LeavePolicy.id == balance_data.policy_id,
        models.LeavePolicy.is_active == True
    ).first()

    if not policy:
        raise HTTPException(
            status_code=404,
            detail="Active leave policy not found"
        )

    if balance_data.allocated_days < 0:
        raise HTTPException(
            status_code=400,
            detail="Allocated days cannot be negative"
        )

    existing = db.query(models.LeaveBalance).filter(
        models.LeaveBalance.employee_id == balance_data.employee_id,
        models.LeaveBalance.policy_id == balance_data.policy_id,
        models.LeaveBalance.year == balance_data.year
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Leave balance already exists for this employee, policy, and year"
        )

    balance = models.LeaveBalance(
        employee_id=balance_data.employee_id,
        policy_id=balance_data.policy_id,
        year=balance_data.year,
        allocated_days=balance_data.allocated_days,
        used_days=0
    )

    db.add(balance)
    db.commit()
    db.refresh(balance)

    return balance

@app.get("/leave-balances")
def get_all_leave_balances(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    return db.query(models.LeaveBalance).all()
  
@app.get("/leave-balances/{employee_id}")
def get_leave_balance(
    employee_id: int,
    year: int,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    # Employees can view only their own balances.
    if user.role not in ["HR", "ADMIN"]:
        employee = db.query(models.Employee).filter(
            models.Employee.user_id == user.id
        ).first()

        if not employee or employee.id != employee_id:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own leave balance"
            )

    balances = db.query(models.LeaveBalance).filter(
        models.LeaveBalance.employee_id == employee_id,
        models.LeaveBalance.year == year
    ).all()

    return [
        {
            "id": balance.id,
            "employee_id": balance.employee_id,
            "policy_id": balance.policy_id,
            "year": balance.year,
            "allocated_days": balance.allocated_days,
            "used_days": balance.used_days,
            "remaining_days": balance.allocated_days - balance.used_days
        }
        for balance in balances
    ]

  
@app.put("/admin/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    admin=Depends(allow_roles("ADMIN"))
):
    allowed_roles = ["ADMIN", "HR", "EMPLOYEE"]

    role = role.upper()

    if role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Role must be ADMIN, HR, or EMPLOYEE"
        )

    user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.role = role
    db.commit()
    db.refresh(user)

    return {
        "message": "User role updated successfully",
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    }

  
@app.get("/admin/users")
def get_admin_users(
    db: Session = Depends(get_db),
    admin=Depends(allow_roles("ADMIN"))
):
    users = db.query(models.User).all()

    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
        for user in users
    ]

@app.get("/leaves/calendar", tags=["Leave Management"])
def leave_calendar(
    db: Session = Depends(get_db),
):
    leaves = db.query(Leave).filter(
        Leave.status == "APPROVED"
    ).all()

    return [
        {
            "id": leave.id,
            "employee_id": leave.employee_id,
            "start_date": leave.start_date,
            "end_date": leave.end_date,
            "reason": leave.reason,
            "status": leave.status,
        }
        for leave in leaves
    ]

@app.get("/leaves/team-availability", tags=["Leave Management"])
def get_team_availability(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()

    result = []

    for employee in employees:
        approved_leaves = db.query(Leave).filter(
            Leave.employee_id == employee.id,
            Leave.status == "APPROVED"
        ).all()

        result.append({
            "employee_id": employee.id,
            "employee_name": employee.full_name,
            "approved_leaves": [
                {
                    "start_date": leave.start_date,
                    "end_date": leave.end_date,
                    "reason": leave.reason
                }
                for leave in approved_leaves
            ]
        })

    return result
