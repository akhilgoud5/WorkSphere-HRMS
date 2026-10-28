
import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_user, allow_roles
from app.models import Employee
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)


@router.get("/employees/csv")
def export_employees_csv(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    employees = db.query(Employee).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Full Name",
        "Designation",
        "Department",
        "Joining Date",
        "Salary",
        "Status"
    ])

    for employee in employees:
        writer.writerow([
            employee.id,
            employee.full_name,
            employee.designation,
            employee.department,
            employee.joining_date,
            employee.salary,
            employee.status
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=employees_report.csv"
        }
    )

@router.get("/employees/pdf")
def export_employees_pdf(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    employees = db.query(Employee).all()

    output = io.BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4)
    )

    data = [
        [
            "ID",
            "Full Name",
            "Designation",
            "Department",
            "Joining Date",
            "Salary",
            "Status"
        ]
    ]

    for employee in employees:
        data.append([
            employee.id,
            employee.full_name,
            employee.designation,
            employee.department,
            str(employee.joining_date or ""),
            employee.salary,
            employee.status
        ])

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))

    doc.build([table])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                "attachment; filename=employees_report.pdf"
        }
    )
