
from app.database import SessionLocal
from app import models

db = SessionLocal()

try:
    users = db.query(models.User).all()

    print("\n--- WorkSphere HRMS Accounts ---")

    for user in users:
        print(
            f"ID: {user.id} | "
            f"Username: {user.username} | "
            f"Role: {user.role}"
        )

    if any(user.role == "ADMIN" for user in users):
        print("\nADMIN account exists.")
    else:
        print("\nNo ADMIN account found.")

finally:
    db.close()
