from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from . import models, schemas
from .security import hash_password, verify_password, create_access_token
from .dependencies import current_user, allow_roles
from datetime import datetime, date
from fastapi.security import OAuth2PasswordRequestForm
from .models import Payroll

Base.metadata.create_all(bind=engine)
app = FastAPI(title="WorkSphere HRMS API", version="1.0.0",
              description="Starter API for WorkSphere HR Management System")

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

    token = create_access_token(str(user.id))

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

    access_token = create_access_token(str(user.id))

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

    employees = query.order_by(models.Employee.id.desc()).all()
    results = []

    for employee in employees:
        employee_data = schemas.EmployeeOut.model_validate(
            employee
        ).model_dump()

        # Prefer the email saved directly on the employee.
        email = employee.email

        # Use the linked user's email only if the employee email is empty.
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


@app.post("/attendance/check-in")
def check_in(
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

    today = date.today()
    record = db.query(models.Attendance).filter(
        models.Attendance.employee_id == employee.id,
        models.Attendance.attendance_date == today
    ).first()

    if record and record.check_in:
        raise HTTPException(
            status_code=400,
            detail="Already checked in today"
        )

    if not record:
        record = models.Attendance(
            employee_id=employee.id,
            attendance_date=today,
            check_in=datetime.now(),
            status="PRESENT"
        )
        db.add(record)
    else:
        record.check_in = datetime.now()

    db.commit()
    db.refresh(record)
    return record


@app.post("/attendance/check-out")
def check_out(
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

    record = db.query(models.Attendance).filter(
        models.Attendance.employee_id == employee.id,
        models.Attendance.attendance_date == date.today()
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

    record.check_out = datetime.now()
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


@app.get("/employees", response_model=list[schemas.EmployeeOut])
def list_employees(
    search: str = "",
    department: str = "",
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

    employees = query.order_by(models.Employee.id.desc()).all()

    results = []

    for employee in employees:
        employee_data = schemas.EmployeeOut.model_validate(employee).model_dump()

        linked_user = None
        if employee.user_id is not None:
            linked_user = (
                db.query(models.User)
                .filter(models.User.id == employee.user_id)
                .first()
            )

        employee_data["email"] = linked_user.email if linked_user else None
        results.append(employee_data)

    return results

@app.post("/leaves", status_code=201)
def apply_leave(
    start_date: date,
    end_date: date,
    reason: str,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="End date cannot be before start date"
        )

    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    leave = models.Leave(
        employee_id=employee.id,
        start_date=start_date,
        end_date=end_date,
        reason=reason
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
    if status.upper() not in ["APPROVED", "REJECTED"]:
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

    leave.status = status.upper()
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

    if basic_salary < 0 or deductions < 0:
        raise HTTPException(
            status_code=400,
            detail="Salary and deductions cannot be negative"
        )

    if deductions > basic_salary:
        raise HTTPException(
            status_code=400,
            detail="Deductions cannot exceed basic salary"
        )

    payroll = models.Payroll(
        employee_id=employee_id,
        month=month,
        basic_salary=basic_salary,
        deductions=deductions,
        net_salary=basic_salary - deductions,
        payment_status="PENDING"
    )

    db.add(payroll)
    db.commit()
    db.refresh(payroll)

    return payroll

@app.get("/payroll")
def get_payroll(
    db: Session = Depends(get_db)
):
    return db.query(Payroll).all()


@app.get("/payroll/{payroll_id}")
def get_payroll_by_id(
    payroll_id: int,
    db: Session = Depends(get_db),
   user = Depends(current_user)
):
    payroll = db.query(Payroll).filter(
        Payroll.id == payroll_id
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
    user=Depends(current_user)
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

    total_payroll = db.query(models.Payroll).count()

    paid_payroll = db.query(models.Payroll).filter(
        models.Payroll.payment_status == "PAID"
    ).count()

    total_payroll_amount = db.query(
        models.Payroll.net_salary
    ).filter(
        models.Payroll.payment_status == "PAID"
    ).all()

    paid_amount = sum(
        float(row[0] or 0) for row in total_payroll_amount
    )

    return {
        "total_users": total_users,
        "total_employees": total_employees,
        "active_employees": active_employees,
        "total_attendance_records": total_attendance,
        "total_leave_requests": total_leaves,
        "pending_leave_requests": pending_leaves,
        "total_payroll_records": total_payroll,
        "paid_payroll_records": paid_payroll,
        "total_paid_salary": paid_amount
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




  

  