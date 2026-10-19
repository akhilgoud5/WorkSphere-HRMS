from app.database import SessionLocal
from app.models import User, Employee

db = SessionLocal()

try:
    user = db.query(User).filter(
        User.username == "akhil_admin"
    ).first()

    employee = db.query(Employee).filter(
        Employee.full_name == "Test Employee"
    ).first()

    if not user:
        print("HR user not found")
    elif not employee:
        print("Employee not found")
    elif employee.user_id not in (None, user.id):
        print("Employee is already linked to another user")
    else:
        employee.user_id = user.id
        db.commit()
        print("Employee linked successfully!")
        print("User ID:", user.id)
        print("Employee ID:", employee.id)

finally:
    db.close()