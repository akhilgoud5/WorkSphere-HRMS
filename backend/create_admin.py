
from getpass import getpass

from app.database import SessionLocal
from app import models
from app.security import hash_password


def main():
    db = SessionLocal()

    try:
        User = models.User
        columns = set(User.__table__.columns.keys())

        if "role" not in columns:
            raise RuntimeError("User model has no role column.")

        if not any(
            getattr(user, "role", "") == "ADMIN"
            for user in db.query(User).all()
        ):
            print("No ADMIN account exists.")
        else:
            print("An ADMIN account already exists.")
            return

        username = input("New ADMIN username: ").strip()
        email = input("New ADMIN email: ").strip().lower()

        if not username or not email or "@" not in email:
            print("Enter a valid username and email.")
            return

        if db.query(User).filter(
            User.username == username
        ).first():
            print("That username already exists.")
            return

        if db.query(User).filter(
            User.email == email
        ).first():
            print("That email already exists.")
            return

        password_field = next(
            (
                field for field in (
                    "hashed_password",
                    "password_hash",
                    "hashed_pass"
                )
                if field in columns
            ),
            None
        )

        if not password_field:
            raise RuntimeError(
                "Password field not identified. "
                "Check app/models.py before continuing."
            )

        password = getpass("New ADMIN password: ")
        confirm = getpass("Confirm ADMIN password: ")

        if len(password) < 12:
            print("Use a password with at least 12 characters.")
            return

        if password != confirm:
            print("Passwords do not match.")
            return

        user = User(
            username=username,
            email=email,
            role="ADMIN",
            **{password_field: hash_password(password)}
        )

        db.add(user)
        db.commit()

        print("ADMIN account created successfully.")
        print("Username:", username)
        print("Role: ADMIN")
        print("Now log in and verify the account.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
