"""One-off seed script: promote a phone number to admin+validator roles.

Usage:
    python scripts/seed_admin.py +263771234567

This talks directly to the database and is meant to be run by whoever
controls the server (e.g. once, after first deploy) — it is intentionally
NOT exposed as an API endpoint, since privilege escalation must never be
reachable over HTTP.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.user import User


def main(phone: str):
    if phone.startswith("07"):
        phone = "+263" + phone[1:]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            user = User(phone=phone, language="en", roles=["farmer", "admin", "validator"])
            db.add(user)
            print(f"Created new admin user {phone}")
        else:
            roles = set(user.roles or [])
            roles.update({"admin", "validator"})
            user.roles = list(roles)
            print(f"Promoted existing user {phone} to {user.roles}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/seed_admin.py <phone>")
        sys.exit(1)
    main(sys.argv[1])
