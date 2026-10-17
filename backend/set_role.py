
import sys
from app.database import SessionLocal
from app.models import User

if len(sys.argv) != 2:
    print("Usage: python set_role.py <username>")
    raise SystemExit(1)

username = sys.argv[1]
db = SessionLocal()

try:
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        print(f"User '{username}' was not found.")
    else:
        user.role = "HR"
        db.commit()
        print(f"Success! {username} now has the HR role.")
finally:
    db.close()
