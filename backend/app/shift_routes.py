from datetime import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .dependencies import allow_roles, current_user


router = APIRouter(tags=["Shift Management"])


# -------------------------------
# Pydantic schemas
# -------------------------------

class ShiftCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    start_time: time
    end_time: time


class ShiftOut(BaseModel):
    id: int
    name: str
    start_time: time
    end_time: time

    model_config = {"from_attributes": True}


class EmployeeShiftCreate(BaseModel):
    employee_id: int = Field(gt=0)
    shift_id: int = Field(gt=0)


class EmployeeShiftOut(BaseModel):
    id: int
    employee_id: int
    shift_id: int

    model_config = {"from_attributes": True}


# -------------------------------
# Create a shift
# HR and ADMIN only
# -------------------------------

@router.post("/shifts/", response_model=ShiftOut, status_code=201)
def create_shift(
    data: ShiftCreate,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN")),
):
    name = data.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Shift name cannot be empty",
        )

    existing = db.query(models.Shift).filter(
        models.Shift.name.ilike(name)
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="A shift with this name already exists",
        )

    shift = models.Shift(
        name=name,
        start_time=data.start_time,
        end_time=data.end_time,
    )

    db.add(shift)
    db.commit()
    db.refresh(shift)

    return shift


# -------------------------------
# List all shifts
# Authenticated users
# -------------------------------

@router.get("/shifts/", response_model=list[ShiftOut])
def list_shifts(
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    return db.query(models.Shift).order_by(
        models.Shift.id
    ).all()


# -------------------------------
# Assign a shift to an employee
# HR and ADMIN only
# -------------------------------

@router.post(
    "/employee-shifts/",
    response_model=EmployeeShiftOut,
    status_code=201,
)
def assign_shift(
    data: EmployeeShiftCreate,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN")),
):
    employee = db.query(models.Employee).filter(
        models.Employee.id == data.employee_id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    if employee.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Cannot assign a shift to an inactive employee",
        )

    shift = db.query(models.Shift).filter(
        models.Shift.id == data.shift_id
    ).first()

    if not shift:
        raise HTTPException(
            status_code=404,
            detail="Shift not found",
        )

    assignment = db.query(models.EmployeeShift).filter(
        models.EmployeeShift.employee_id == data.employee_id
    ).first()

    if assignment:
        # Update the employee's existing assignment.
        assignment.shift_id = data.shift_id
    else:
        assignment = models.EmployeeShift(
            employee_id=data.employee_id,
            shift_id=data.shift_id,
        )
        db.add(assignment)

    db.commit()
    db.refresh(assignment)

    return assignment


# -------------------------------
# View an employee's shift
# -------------------------------

@router.get(
    "/employee-shifts/{employee_id}",
)
def get_employee_shift(
    employee_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    # Employees may view their own shift.
    # HR and ADMIN may view any employee's shift.
    if user.role not in ["HR", "ADMIN"]:
        employee = db.query(models.Employee).filter(
            models.Employee.user_id == user.id
        ).first()

        if not employee or employee.id != employee_id:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own shift",
            )

    assignment = db.query(models.EmployeeShift).filter(
        models.EmployeeShift.employee_id == employee_id
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="No shift assigned to this employee",
        )

    shift = db.query(models.Shift).filter(
        models.Shift.id == assignment.shift_id
    ).first()

    return {
        "assignment_id": assignment.id,
        "employee_id": assignment.employee_id,
        "shift_id": shift.id,
        "shift_name": shift.name,
        "start_time": shift.start_time,
        "end_time": shift.end_time,
    }