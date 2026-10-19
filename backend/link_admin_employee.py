from datetime import date
from app.database import SessionLocal
from app.models import User, Employee

db = SessionLocal()

try:
    admin = db.query(User).filter(
        User.username == "akhil_admin"
    ).first()

    if not admin:
        print("Admin user not found")
    else:
        employee = db.query(Employee).filter(
            Employee.user_id == admin.id
        ).first()

        if employee:
            print("Admin already has an employee profile")
            print("Employee ID:", employee.id)
        else:
            employee = Employee(
                user_id=admin.id,
                full_name=admin.username,
                designation="Administrator",
                department="Administration",
                joining_date=date.today(),
                salary=0,
                status="ACTIVE"
            )

            db.add(employee)
            db.commit()
            db.refresh(employee)

            print("Admin employee profile created!")
            print("User ID:", admin.id)
            print("Employee ID:", employee.id)

except Exception as e:
    db.rollback()
    print("Error:", e)

finally:
    db.close()