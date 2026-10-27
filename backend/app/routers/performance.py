
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, Performance
from app.dependencies import current_user, allow_roles

router = APIRouter(prefix="/performance", tags=["Performance"])


class PerformanceCreate(BaseModel):
    employee_id: int
    review_period: str = Field(..., min_length=1, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    feedback: str = Field(..., min_length=1, max_length=1000)


@router.post("/", status_code=201)
def create_performance_review(
    data: PerformanceCreate,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN")),
):
    employee = db.query(Employee).filter(
        Employee.id == data.employee_id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    review = Performance(
        employee_id=data.employee_id,
        review_period=data.review_period,
        rating=data.rating,
        feedback=data.feedback,
        created_at=datetime.utcnow(),
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    return review


@router.get("/")
def list_performance_reviews(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN")),
):
    return db.query(Performance).order_by(
        Performance.created_at.desc()
    ).all()


@router.get("/employee/{employee_id}")
def get_employee_performance(
    employee_id: int,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN")),
):
    employee = db.query(Employee).filter(
        Employee.id == employee_id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    return db.query(Performance).filter(
        Performance.employee_id == employee_id
    ).order_by(Performance.created_at.desc()).all()
