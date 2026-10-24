
from app.database import SessionLocal
from app.models import User, Employee

db = SessionLocal()

try:
    user = db.query(User).filter(
        User.username == "akhil5"
    ).first()

    employee = db.query(Employee).filter(
        Employee.id == 7
    ).first()

    if not user:
        print("User akhil5 not found")
    elif not employee:
        print("Employee ID 7 not found")
    elif employee.user_id not in (None, user.id):
        print("Employee already linked to another user")
    else:
        existing = db.query(Employee).filter(
            Employee.user_id == user.id
        ).first()

        if existing and existing.id != employee.id:
            print("User already linked to another employee")
            print("Existing employee ID:", existing.id)
        else:
            employee.user_id = user.id
            db.commit()
            print("Employee linked successfully")
            print("User ID:", user.id)
            print("Employee ID:", employee.id)

finally:
    db.close()
