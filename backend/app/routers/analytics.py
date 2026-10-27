
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.dependencies import allow_roles
from app.models import Employee, Attendance, Leave, Performance

router = APIRouter(
    prefix="/analytics",
    tags=["HR Analytics"]
)


@router.get("/employees")
def employee_analytics(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    total = db.query(Employee).count()

    active = db.query(Employee).filter(
        Employee.status == "ACTIVE"
    ).count()

    inactive = db.query(Employee).filter(
        Employee.status == "INACTIVE"
    ).count()

    return {
        "total_employees": total,
        "active_employees": active,
        "inactive_employees": inactive
    }


@router.get("/departments")
def department_analytics(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    results = db.query(
        Employee.department,
        func.count(Employee.id).label("employee_count")
    ).group_by(Employee.department).all()

    return [
        {
            "department": department or "Unassigned",
            "employee_count": count
        }
        for department, count in results
    ]


@router.get("/attendance")
def attendance_analytics(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    results = db.query(
        Attendance.status,
        func.count(Attendance.id).label("record_count")
    ).group_by(Attendance.status).all()

    return [
        {
            "status": status,
            "record_count": count
        }
        for status, count in results
    ]


@router.get("/leaves")
def leave_analytics(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    results = db.query(
        Leave.status,
        func.count(Leave.id).label("leave_count")
    ).group_by(Leave.status).all()

    return [
        {
            "status": status,
            "leave_count": count
        }
        for status, count in results
    ]


@router.get("/performance")
def performance_analytics(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    result = db.query(
        func.count(Performance.id).label("total_reviews"),
        func.avg(Performance.rating).label("average_rating")
    ).first()

    return {
        "total_reviews": result.total_reviews or 0,
        "average_rating": round(float(result.average_rating), 2)
        if result.average_rating is not None else 0
    }
