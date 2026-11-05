
from getpass import getpass

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password


def create_admin():
    db = SessionLocal()

    try:
        email = input("Admin email: ").strip().lower()
        full_name = input("Admin full name: ").strip()

        existing_user = db.scalar(
            select(User).where(User.email == email)
        )

        if existing_user:
            print("An account with this email already exists.")
            print("No changes were made.")
            return

        password = getpass("Admin password: ")
        confirm_password = getpass("Confirm password: ")

        if password != confirm_password:
            print("Passwords do not match.")
            return

        if len(password) < 8:
            print("Password must contain at least 8 characters.")
            return

        admin = User(
            full_name=full_name,
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print("Administrator account created successfully.")

    except Exception as error:
        db.rollback()
        print("Unable to create administrator:", error)

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
