from app.database import SessionLocal
from app import models

db = SessionLocal()

try:
    print("\n--- USERS ---")
    for user in db.query(models.User).order_by(models.User.id).all():
        print(
            f"User ID: {user.id} | "
            f"Username: {user.username} | "
            f"Email: {user.email}"
        )

    print("\n--- EMPLOYEES ---")
    for employee in db.query(models.Employee).order_by(models.Employee.id).all():
        user = None

        if employee.user_id is not None:
            user = db.query(models.User).filter(
                models.User.id == employee.user_id
            ).first()

        print(
            f"Employee ID: {employee.id} | "
            f"Name: {employee.full_name} | "
            f"User ID: {employee.user_id} | "
            f"Email: {user.email if user else '-'}"
        )
finally:
    db.close()