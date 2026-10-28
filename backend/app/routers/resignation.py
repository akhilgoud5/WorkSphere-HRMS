
from datetime import date
from typing import Optional
from app.models import Employee, Resignation
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee
from app.dependencies import current_user, allow_roles

router = APIRouter(
    prefix="/resignations",
    tags=["Resignation & Exit Management"]
)


# Request schema
class ResignationCreate(BaseModel):
    reason: str
    proposed_last_working_date: date


# Response schema
class ResignationOut(BaseModel):
    id: int
    employee_id: int
    reason: str
    proposed_last_working_date: date
    status: str

    class Config:
        from_attributes = True


# Create resignation request
@router.post("/", response_model=ResignationOut, status_code=201)
def submit_resignation(
    data: ResignationCreate,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    employee = db.query(Employee).filter(
        Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee record not found"
        )

    if data.proposed_last_working_date <= date.today():
        raise HTTPException(
            status_code=400,
            detail="Last working date must be in the future"
        )

    resignation = Resignation(
        employee_id=employee.id,
        reason=data.reason,
        proposed_last_working_date=data.proposed_last_working_date,
        status="PENDING"
    )

    db.add(resignation)
    db.commit()
    db.refresh(resignation)

    return resignation


# View all resignation requests (HR/Admin)
@router.get("/", response_model=list[ResignationOut])
def get_resignations(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    return db.query(Resignation).all()


# Approve or reject a resignation (HR/Admin)
@router.put("/{resignation_id}/decision")
def decide_resignation(
    resignation_id: int,
    decision: str,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    resignation = db.query(Resignation).filter(
        Resignation.id == resignation_id
    ).first()

    if not resignation:
        raise HTTPException(
            status_code=404,
            detail="Resignation request not found"
        )

    decision = decision.upper()

    if decision not in ["APPROVED", "REJECTED"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be APPROVED or REJECTED"
        )

    if resignation.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="This resignation has already been processed"
        )

    resignation.status = decision
    db.commit()
    db.refresh(resignation)

    return resignation
