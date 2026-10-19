from app.database import SessionLocal
from app.models import User, Employee

db = SessionLocal()

try:
    user = db.query(User).filter(
        User.username == "Akhil1"
    ).first()

    if not user:
        print("HR user not found")
    else:
        existing = db.query(Employee).filter(
            Employee.user_id == user.id
        ).first()

        if existing:
            print("Employee profile already exists:", existing.id)
        else:
            employee = Employee(
                user_id=user.id,
                full_name="Akhil1",
                designation="HR",
                department="Human Resources",
                salary=30000,
                status="ACTIVE"
            )

            db.add(employee)
            db.commit()
            db.refresh(employee)

            print("HR employee profile created!")
            print("Employee ID:", employee.id)
            print("User ID:", employee.user_id)

finally:
    db.close()