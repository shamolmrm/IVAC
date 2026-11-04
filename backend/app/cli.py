"""Admin commands, run inside the API container:

    docker exec -it ivac-api python -m app.cli create-superadmin you@example.com "Full Name"

The password is asked interactively (never passed on the command line).
"""

import getpass
import sys

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.db import get_sessionmaker
from app.modules.audit.service import audit
from app.modules.auth.models import User
from app.modules.auth.security import hash_password


def create_superadmin(email: str, full_name: str) -> None:
    email = email.strip().lower()
    with get_sessionmaker()() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.is_superadmin = True
            print(f"{email} is now a super admin.")
        else:
            password = getpass.getpass("Password (min 10 chars): ")
            if len(password) < 10 or password != getpass.getpass("Repeat: "):
                sys.exit("Passwords must match and be at least 10 characters.")
            user = User(email=email, full_name=full_name, password_hash=hash_password(password),
                        is_superadmin=True)
            db.add(user)
            db.flush()
            print(f"Created super admin {email}.")
        audit(db, "user.superadmin_granted", target_type="user", target_id=user.id,
              detail={"via": "cli"})
        db.commit()


def main(argv: list[str]) -> None:
    if len(argv) >= 2 and argv[0] == "create-superadmin":
        create_superadmin(argv[1], argv[2] if len(argv) > 2 else argv[1].split("@")[0])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
