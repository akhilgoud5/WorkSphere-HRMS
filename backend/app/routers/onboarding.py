
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Onboarding, Employee
from app.schemas import (OnboardingCreate,OnboardingStatusUpdate, OnboardingOut,)
from app.dependencies import current_user as get_logged_in_user

router = APIRouter(
    prefix="/onboarding",
    tags=["Employee Onboarding"],
)


# Assign an onboarding task (HR/Admin only)
@router.post("/", response_model=OnboardingOut, status_code=201)
def create_onboarding_task(
    data: OnboardingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_logged_in_user),
):
    if current_user.role not in ["HR", "ADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="Only HR or Admin can assign onboarding tasks",
        )

    employee = db.query(Employee).filter(
        Employee.id == data.employee_id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    task = Onboarding(
        employee_id=data.employee_id,
        task_name=data.task_name,
        due_date=data.due_date,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


# View the current employee's onboarding checklist
@router.get("/me", response_model=list[OnboardingOut])
def get_my_onboarding_tasks(
    db: Session = Depends(get_db),
    current_user=Depends(get_logged_in_user),
):
    employee = db.query(Employee).filter(
        Employee.user_id == current_user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found",
        )

    return db.query(Onboarding).filter(
        Onboarding.employee_id == employee.id
    ).all()


# View an employee's onboarding tasks (HR/Admin)
@router.get("/{employee_id}", response_model=list[OnboardingOut])
def get_employee_onboarding_tasks(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_logged_in_user),
):
    if current_user.role not in ["HR", "ADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="Only HR or Admin can view another employee's tasks",
        )

    employee = db.query(Employee).filter(
        Employee.id == employee_id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    return db.query(Onboarding).filter(
        Onboarding.employee_id == employee_id
    ).all()


# Update an onboarding task's status
@router.patch("/{task_id}/status", response_model=OnboardingOut)
def update_onboarding_status(
    task_id: int,
    data: OnboardingStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_logged_in_user),
):
    task = db.query(Onboarding).filter(
        Onboarding.id == task_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Onboarding task not found",
        )

    if current_user.role not in ["HR", "ADMIN"]:
        employee = db.query(Employee).filter(
            Employee.user_id == current_user.id
        ).first()

        if not employee or employee.id != task.employee_id:
            raise HTTPException(
                status_code=403,
                detail="You can only update your own onboarding tasks",
            )

    task.status = data.status
    db.commit()
    db.refresh(task)

    return task


# Track onboarding progress (HR/Admin)
@router.get("/{employee_id}/progress")
def get_onboarding_progress(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_logged_in_user),
):
    if current_user.role not in ["HR", "ADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="Only HR or Admin can view onboarding progress",
        )

    employee = db.query(Employee).filter(
        Employee.id == employee_id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    tasks = db.query(Onboarding).filter(
        Onboarding.employee_id == employee_id
    ).all()

    total = len(tasks)
    completed = sum(1 for task in tasks if task.status == "COMPLETED")

    return {
        "employee_id": employee_id,
        "total_tasks": total,
        "completed_tasks": completed,
        "pending_tasks": total - completed,
        "progress_percentage": round(
            (completed / total) * 100, 2
        ) if total else 0,
    }
