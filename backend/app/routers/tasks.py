from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import Optional

from app.database import get_db
from app.models import Task
from app.dependencies import current_user, allow_roles

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)


class TaskCreate(BaseModel):
    assigned_to: int
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None


class TaskStatusUpdate(BaseModel):
    status: str


@router.post("/")
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    task = Task(
        assigned_to=data.assigned_to,
        title=data.title,
        description=data.description,
        due_date=data.due_date
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


@router.get("/")
def get_tasks(
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    if user.role in ["HR", "ADMIN"]:
        return db.query(Task).all()

    employee = db.query(
        __import__("app.models", fromlist=["Employee"]).Employee
    ).filter_by(user_id=user.id).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    return db.query(Task).filter(
        Task.assigned_to == employee.id
    ).all()


@router.patch("/{task_id}/status")
def update_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    if data.status not in ["PENDING", "COMPLETED"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be PENDING or COMPLETED"
        )

    task = db.query(Task).filter(
        Task.id == task_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    if user.role not in ["HR", "ADMIN"]:
        employee = db.query(
            __import__("app.models", fromlist=["Employee"]).Employee
        ).filter_by(user_id=user.id).first()

        if not employee or task.assigned_to != employee.id:
            raise HTTPException(
                status_code=403,
                detail="You can update only your own tasks"
            )

    task.status = data.status
    db.commit()
    db.refresh(task)

    return task